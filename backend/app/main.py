"""API FastAPI del backend local. Expone el mismo contrato que el frontend ya
consume (POST /api/verify), pero resuelto con LLM local (Ollama) + RAG (Chroma).
No genera audio: la voz (TTS/STT) la maneja el navegador."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from . import access, config, events, invitations, llm, ocr, prompt, qr, rag, softia, stt, sync
from .schemas import (
    Action,
    Animation,
    GateResponse,
    IdentifyRequest,
    QRVerifyRequest,
    Status,
    VerifyRequest,
    VerifyResponse,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("guard-backend")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Arranca la sincronización periódica con Soft-IA si está habilitada."""
    task = None
    if config.SOFTIA_ENABLED and config.CONDOMINIO_ID:
        logger.info("Sincronización con Soft-IA habilitada (cada %ss)", config.SOFTIA_SYNC_INTERVAL)
        task = asyncio.create_task(sync.sync_loop())
    else:
        logger.info("Sincronización con Soft-IA deshabilitada (usa datos locales)")
    try:
        yield
    finally:
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


app = FastAPI(title="SoftiaGuard - Vigilante Virtual (backend local)", lifespan=lifespan)

# El tótem/navegador puede llamar desde el mismo origen (proxy Vite) o directo.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Respuesta de contingencia idéntica en espíritu a la del backend original (server.ts:115)
ERROR_RESPONSE = VerifyResponse(
    reply=(
        "Disculpe las molestias, estoy experimentando dificultades técnicas para "
        "conectar con la base de datos de seguridad. Por favor, intente de nuevo o "
        "presione el Botón de Pánico."
    ),
    apartment=None,
    status=Status.ERROR,
    owner=None,
    action=Action.show_error,
    assistant_animation=Animation.denied,
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "llm_model": config.LLM_MODEL, "embed_model": config.EMBED_MODEL}


@app.post("/api/sync")
async def trigger_sync() -> dict:
    """Fuerza una sincronización con Soft-IA (además de la periódica). Útil para
    pruebas y para refrescar bajo demanda."""
    return await sync.sync_once()


@app.get("/api/apartments")
def list_apartments() -> list:
    """Paridad con el backend original (server.ts:127). El frontend actual no lo usa."""
    return rag.load_apartments()


# Mensajes de denegación por motivo de rechazo del QR
QR_DENY_MESSAGES = {
    "invalid_format": "No pude leer el código QR. Verifique que sea una invitación válida.",
    "not_found": "Esta invitación no está registrada o ya no es válida. Por favor, contacte al residente.",
    "wrong_condominio": "Este código QR pertenece a otro condominio y no es válido aquí.",
    "vetado": "Lo siento, el acceso de este visitante está restringido. Por favor, contacte a la administración.",
    "inactivo": "Esta invitación no se encuentra activa. Por favor, contacte al residente.",
    "expired": "Su autorización de visita ha vencido. Por favor, solicite una nueva al residente.",
}


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


# --- Compuerta de autorización (compartida por QR y voz/nombre) ------------------

_NEED_INFO_PROMPTS = {
    "cedula": "Su autorización no tiene la cédula registrada. Por favor, muestre su cédula de identidad a la cámara.",
    "telefono": "Por favor, indíqueme un número de teléfono de contacto.",
    "nombre": "Por favor, dígame su nombre completo.",
    "apartment": "Hay varias autorizaciones con ese nombre. ¿A qué apartamento viene?",
}


def _need_info_response(record: Optional[dict], missing: list) -> GateResponse:
    # Pide un dato a la vez, priorizando cédula (cámara) y luego teléfono.
    order = ["cedula", "telefono", "nombre", "apartment"]
    field = next((f for f in order if f in missing), missing[0] if missing else "")
    action = Action.show_id_scanner if field == "cedula" else Action.collect_info
    return GateResponse(
        reply=_NEED_INFO_PROMPTS.get(field, "Necesito algunos datos adicionales para continuar."),
        apartment=(record or {}).get("inmueble"),
        status=Status.NEED_INFO,
        owner=(record or {}).get("propietario"),
        action=action,
        assistant_animation=Animation.talking,
        missing=missing,
        auth_id=str((record or {}).get("id")) if record else None,
    )


def _approved_response(record: dict, background_tasks: BackgroundTasks) -> GateResponse:
    nombre = record.get("nombre") or "Visitante"
    inmueble = record.get("inmueble")
    propietario = record.get("propietario")
    # RF-14: registrar la visita en Soft-IA (en segundo plano, offline-first).
    if config.SOFTIA_ENABLED and config.CONDOMINIO_ID:
        visita = {
            "idpropietario": _to_int(record.get("idpropietario")),
            "idvisita": _to_int(record.get("id")),
            "autorizado_por": config.SOFTIA_AUTORIZADO_POR,
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "telefono": record.get("telefono") or "",
        }
        background_tasks.add_task(events.register_or_queue, config.CONDOMINIO_ID, visita)
    return GateResponse(
        reply=(
            f"¡Bienvenido, {nombre}! Su invitación al inmueble {inmueble} "
            f"(residencia de {propietario}) es válida. Abriendo el portón."
        ),
        apartment=inmueble,
        status=Status.APPROVED,
        owner=propietario,
        action=Action.open_gate,
        assistant_animation=Animation.success,
        auth_id=str(record.get("id")),
    )


def _denied_response(reason: str, record: Optional[dict] = None) -> GateResponse:
    return GateResponse(
        reply=QR_DENY_MESSAGES.get(reason, "Acceso denegado."),
        apartment=(record or {}).get("inmueble"),
        status=Status.DENIED,
        owner=(record or {}).get("propietario"),
        action=Action.show_error,
        assistant_animation=Animation.denied,
    )


@app.post("/api/verify-qr", response_model=GateResponse)
async def verify_qr(request: QRVerifyRequest, background_tasks: BackgroundTasks) -> GateResponse:
    """Valida el QR de invitación de Soft-IA. El QR aporta el `id`; la decisión se toma
    con el estado real del libro mayor. Si faltan datos ({nombre, cédula, teléfono}),
    devuelve NEED_INFO para completarlos antes de autorizar."""
    try:
        payload = qr.parse_qr(request.code)
        if not payload:
            return _denied_response("invalid_format")
        record = invitations.find_authorization(payload.get("id"))
        if not record:
            return _denied_response("not_found")

        result = access.evaluate(record)
        if result["outcome"] == "need_info":
            return _need_info_response(record, result["missing"])
        if result["outcome"] == "ok":
            return _approved_response(record, background_tasks)
        return _denied_response(result["reason"], record)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Fallo en /api/verify-qr: %s", exc)
        return GateResponse(**ERROR_RESPONSE.model_dump())


@app.post("/api/identify", response_model=GateResponse)
async def identify(request: IdentifyRequest, background_tasks: BackgroundTasks) -> GateResponse:
    """Identificación por nombre y recolección de datos faltantes. El frontend acumula
    los datos y reenvía; cuando están completos se actualiza Soft-IA y se decide."""
    try:
        # 1. Obtener la autorización (por id en curso, o resolver por nombre)
        if request.auth_id:
            record = invitations.find_authorization(request.auth_id)
            if not record:
                return _denied_response("not_found")
        else:
            outcome, result = access.resolve_by_name(request.nombre, request.cedula, request.apartment)
            if outcome == "not_found":
                return GateResponse(
                    reply="No encontré una autorización a su nombre. Por favor, verifique con el residente o use el intercomunicador.",
                    status=Status.DENIED, action=Action.show_error, assistant_animation=Animation.denied,
                )
            if outcome == "ambiguous":
                return _need_info_response(None, ["apartment"])
            record = result

        # 2. Aplicar los datos aportados: libro mayor local (inmediato) + Soft-IA (best-effort)
        provided = {}
        if not access._is_empty(request.cedula):
            provided["cedula"] = str(request.cedula).strip()
        if not access._is_empty(request.telefono):
            provided["telefono"] = str(request.telefono).strip()
        if provided:
            auth_id = str(record.get("id"))
            invitations.update_record(auth_id, provided)
            if config.SOFTIA_ENABLED and config.CONDOMINIO_ID:
                try:
                    await softia.update_autorizacion(config.CONDOMINIO_ID, auth_id, provided)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("No se pudo actualizar la autorización en Soft-IA: %s", exc)
            record = invitations.find_authorization(auth_id) or record

        # 3. Evaluar
        result = access.evaluate(record)
        if result["outcome"] == "need_info":
            return _need_info_response(record, result["missing"])
        if result["outcome"] == "ok":
            return _approved_response(record, background_tasks)
        return _denied_response(result["reason"], record)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Fallo en /api/identify: %s", exc)
        return GateResponse(**ERROR_RESPONSE.model_dump())


@app.post("/api/verify-cedula")
async def verify_cedula(file: UploadFile = File(...), auth_id: str = Form("")) -> dict:
    """OCR local de la cédula mostrada a la cámara. Devuelve el número detectado y si
    el nombre reconocido coincide con la autorización (si se pasa `auth_id`)."""
    try:
        image_bytes = await file.read()
        result = ocr.extract_cedula(image_bytes)
        match = None
        if auth_id and not result.get("error"):
            record = invitations.find_authorization(auth_id)
            if record and record.get("nombre"):
                match = access.name_matches(record["nombre"], result.get("text", ""))
        return {"cedula": result.get("cedula"), "match": match, "error": result.get("error")}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Fallo en /api/verify-cedula: %s", exc)
        return {"cedula": None, "match": None, "error": "ocr_failed"}


@app.post("/api/transcribe")
async def transcribe(file: UploadFile = File(...)) -> dict:
    """STT local: recibe un clip de audio del navegador y devuelve el texto.
    100% local (Whisper), sin enviar el audio a ningún servicio externo."""
    try:
        audio_bytes = await file.read()
        text = stt.transcribe(audio_bytes)
        return {"text": text}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Fallo en /api/transcribe: %s", exc)
        return {"text": "", "error": "transcription_failed"}


@app.post("/api/verify", response_model=VerifyResponse)
def verify(request: VerifyRequest) -> VerifyResponse:
    try:
        # 1) Resolución determinista del apartamento (lookup exacto por id/nombre)
        apartment = rag.find_apartment(request.currentAptInput, request.message)

        # 2) Recuperación semántica de políticas/procedimientos relevantes
        query = request.message or ""
        if apartment:
            query = f"{query} {apartment['status']} {apartment['notes']}"
        context_chunks = rag.retrieve_context(query)

        # 3) Prompt con contexto inyectado + 4) generación estructurada con el LLM
        messages = prompt.build_messages(request, apartment, context_chunks)
        result = llm.generate(messages)

        # 5) Reforzar apartment/owner con el dato autoritativo si el modelo los omitió
        if apartment:
            result.apartment = result.apartment or apartment["apt"]
            result.owner = result.owner or apartment["owner"]

        return result

    except Exception as exc:  # noqa: BLE001 - degradar con gracia ante fallo del LLM/RAG
        logger.exception("Fallo en /api/verify: %s", exc)
        return ERROR_RESPONSE


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=config.PORT, reload=True)
