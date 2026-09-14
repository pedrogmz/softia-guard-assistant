"""API FastAPI del backend local. Expone el mismo contrato que el frontend ya
consume (POST /api/verify), pero resuelto con LLM local (Ollama) + RAG (Chroma).
No genera audio: la voz (TTS/STT) la maneja el navegador."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from . import config, invitations, llm, prompt, qr, rag, stt, sync
from .schemas import (
    Action,
    Animation,
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


@app.post("/api/verify-qr", response_model=VerifyResponse)
def verify_qr(request: QRVerifyRequest) -> VerifyResponse:
    """Valida el QR de invitación de Soft-IA. El QR (URL con JSON en base64) aporta
    el `id` de la autorización; la decisión se toma con el ESTADO REAL almacenado en
    el libro mayor `invitations.json` (no con lo que traiga el QR, que es
    falsificable). Objetivo (RF-15): que ese libro mayor sea/consulte a Soft-IA."""
    try:
        payload = qr.parse_qr(request.code)
        if not payload:
            return _qr_denied("invalid_format")

        record = invitations.find_authorization(payload.get("id"))
        if not record:
            return _qr_denied("not_found")

        reason = invitations.check_state(record)
        nombre = record.get("nombre") or "Visitante"
        inmueble = record.get("inmueble")
        propietario = record.get("propietario")

        if reason == "ok":
            return VerifyResponse(
                reply=(
                    f"¡Bienvenido, {nombre}! Su invitación al inmueble {inmueble} "
                    f"(residencia de {propietario}) es válida. Abriendo el portón."
                ),
                apartment=inmueble,
                status=Status.APPROVED,
                owner=propietario,
                action=Action.open_gate,
                assistant_animation=Animation.success,
            )
        return _qr_denied(reason, apt=inmueble, owner=propietario)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Fallo en /api/verify-qr: %s", exc)
        return ERROR_RESPONSE


def _qr_denied(reason: str, apt: Optional[str] = None, owner: Optional[str] = None) -> VerifyResponse:
    return VerifyResponse(
        reply=QR_DENY_MESSAGES.get(reason, "El código QR no es válido."),
        apartment=apt,
        status=Status.DENIED,
        owner=owner,
        action=Action.show_error,
        assistant_animation=Animation.denied,
    )


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
