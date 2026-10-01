"""API FastAPI del backend local. El canal de conversación (POST /api/verify) se
resuelve con LLM local (Ollama) + RAG (Chroma) y solo orienta; la decisión de acceso
sale de /api/verify-qr, /api/identify y la solicitud aprobada por el propietario.
No genera audio: la voz (TTS/STT) la maneja el navegador."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from . import (
    access, access_requests, cedula_proof, config, conversation, events, invitations, llm, ocr,
    prompt, qr, rag, softia, stt, sync,
)
from .schemas import (
    AccessRequestCreate,
    Action,
    Animation,
    GateResponse,
    IdentifyRequest,
    OwnerDecision,
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
    # Solicitud de acceso al propietario (WhatsApp vía Soft-IA)
    "owner_rejected": "Lo siento, el residente no autorizó su visita.",
    "owner_no_answer": "El residente no respondió a tiempo. Puede intentarlo más tarde o comunicarse directamente con él.",
    "request_cancelled": "Solicitud cancelada. Que tenga un buen día.",
    "owner_unreachable": "En este momento no puedo contactar al residente. Por favor, intente más tarde o comuníquese directamente con él.",
    "do_not_disturb": "El residente de ese inmueble pidió no ser molestado. No puedo enviarle solicitudes en este momento.",
    "request_not_found": "No encontré esa solicitud de acceso. Por favor, inicie de nuevo.",
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


# Prompts del modo solicitud (visitante sin autorización): el inmueble es el destino
_REQUEST_PROMPTS = {
    **_NEED_INFO_PROMPTS,
    "apartment": "¿A qué inmueble se dirige? Dígame el número del inmueble o el nombre del propietario.",
    "motivo": "¿Cuál es el motivo de su visita? Si prefiere no indicarlo, diga «ninguno».",
}


def _need_info_response(
    record: Optional[dict], missing: list, request_mode: bool = False, prefix: str = ""
) -> GateResponse:
    # Pide un dato a la vez, priorizando cédula (cámara) y luego teléfono.
    # En modo solicitud primero el destino, y el motivo al final.
    order = (
        ["apartment", "nombre", "cedula", "telefono", "motivo"] if request_mode
        else ["cedula", "telefono", "nombre", "apartment"]
    )
    prompts = _REQUEST_PROMPTS if request_mode else _NEED_INFO_PROMPTS
    field = next((f for f in order if f in missing), missing[0] if missing else "")
    action = Action.show_id_scanner if field == "cedula" else Action.collect_info
    reply = prompts.get(field, "Necesito algunos datos adicionales para continuar.")
    return GateResponse(
        reply=f"{prefix} {reply}".strip(),
        apartment=(record or {}).get("inmueble"),
        status=Status.NEED_INFO,
        owner=(record or {}).get("propietario"),
        action=action,
        assistant_animation=Animation.talking,
        missing=missing,
        auth_id=str((record or {}).get("id")) if record else None,
        request_mode=request_mode,
    )


def _approved_response(
    record: dict, background_tasks: BackgroundTasks,
    reply: Optional[str] = None, register: bool = True,
) -> GateResponse:
    nombre = record.get("nombre") or "Visitante"
    inmueble = record.get("inmueble")
    propietario = record.get("propietario")
    # RF-14: registrar la visita en Soft-IA (en segundo plano, offline-first).
    if register and config.SOFTIA_ENABLED and config.CONDOMINIO_ID:
        visita = {
            "idpropietario": _to_int(record.get("idpropietario")),
            "idvisita": _to_int(record.get("id")),
            "autorizado_por": config.SOFTIA_AUTORIZADO_POR,
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "telefono": record.get("telefono") or "",
        }
        background_tasks.add_task(events.register_or_queue, config.CONDOMINIO_ID, visita)
    return GateResponse(
        reply=reply or (
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
        # 0. Modo solicitud: recoger datos para pedir autorización al propietario
        if request.request_mode:
            return await _request_step(request)

        # 1. Obtener la autorización (por id en curso, o resolver por nombre)
        if request.auth_id:
            record = invitations.find_authorization(request.auth_id)
            if not record:
                return _denied_response("not_found")
        else:
            outcome, result = access.resolve_by_name(request.nombre, request.cedula, request.apartment)
            if outcome == "not_found":
                # Sin autorización: ofrecer la solicitud al propietario (RF-20)
                return await _request_step(
                    request, prefix="No encontré una autorización a su nombre. "
                    "Puedo enviar una solicitud al propietario por WhatsApp.",
                )
            if outcome == "ambiguous":
                return _need_info_response(None, ["apartment"])
            record = result

        # 2. Aplicar los datos aportados: libro mayor local (inmediato) + Soft-IA (best-effort).
        # La cédula solo cuenta con el comprobante de /api/verify-cedula (nombre coincidente)
        # para esta autorización; sin él se ignora y se volverá a pedir a la cámara.
        provided = {}
        if not access._is_empty(request.cedula) and cedula_proof.is_valid(
            request.cedula_token, str(record.get("id")), request.cedula
        ):
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
        if result["reason"] in access.REQUESTABLE_REASONS:
            # Vencida / inactiva: ofrecer una nueva solicitud reutilizando sus datos
            reason = "ha vencido" if result["reason"] == "expired" else "no está activa"
            return await _request_step(
                request.model_copy(update={"auth_id": str(record.get("id"))}),
                prefix=f"Su autorización {reason}. Puedo enviar una solicitud al propietario por WhatsApp.",
            )
        return _denied_response(result["reason"], record)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Fallo en /api/identify: %s", exc)
        return GateResponse(**ERROR_RESPONSE.model_dump())


# --- Solicitud de acceso al propietario por WhatsApp, vía Soft-IA (RF-20..23) ---------

async def _request_step(request: IdentifyRequest, prefix: str = "") -> GateResponse:
    """Un paso del diálogo de solicitud: pide el siguiente dato o, si están todos,
    crea la solicitud. Si hay una autorización previa (vencida/inactiva) reutiliza
    sus datos."""
    record = invitations.find_authorization(request.auth_id) if request.auth_id else None
    base = record or {}
    data = {
        "apartment": request.apartment or base.get("inmueble"),
        "nombre": request.nombre or base.get("nombre"),
        "cedula": request.cedula or base.get("cedula"),
        "telefono": request.telefono or base.get("telefono"),
        "motivo": request.motivo,
    }
    if data["motivo"] is not None and access._norm(data["motivo"]).strip(" .") in ("ninguno", "ninguna", "no"):
        data["motivo"] = ""
    missing = access.missing_for_request(data)
    apartment = None
    if "apartment" not in missing:
        apartment = access.find_destination(data["apartment"])
        if not apartment:
            missing.insert(0, "apartment")
            prefix = (prefix + f" No encontré el inmueble «{data['apartment']}».").strip()
    if missing:
        resp = _need_info_response(record, missing, request_mode=True, prefix=prefix)
        if apartment:
            resp.apartment, resp.owner = apartment.get("apt"), apartment.get("owner")
        return resp
    return await _create_access_request(data, apartment)


async def _create_access_request(data: dict, apartment: dict) -> GateResponse:
    if access.do_not_disturb(apartment):
        return _denied_response("do_not_disturb", {"inmueble": apartment.get("apt")})
    try:
        req = await access_requests.create(data, apartment)
    except Exception as exc:  # noqa: BLE001 - sin cola: una solicitud tardía no sirve
        logger.warning("No se pudo crear la solicitud de acceso en Soft-IA: %s", exc)
        return _denied_response("owner_unreachable", {"inmueble": apartment.get("apt")})
    return _pending_response(
        req,
        f"Listo. Envié su solicitud al propietario del inmueble {req['inmueble']} por WhatsApp. "
        "Por favor, espere unos momentos su respuesta.",
    )


def _pending_response(req: dict, reply: str) -> GateResponse:
    return GateResponse(
        reply=reply,
        apartment=req.get("inmueble"),
        status=Status.PENDING_CONFIRMATION,
        owner=req.get("propietario"),
        action=Action.await_owner,
        assistant_animation=Animation.scanning,
        request_mode=True,
        request_id=req["id"],
        expires_in=access_requests.expires_in(req),
    )


def _request_outcome(req: Optional[dict], background_tasks: BackgroundTasks) -> GateResponse:
    """Traduce el estado de la solicitud a la respuesta del tótem."""
    if not req:
        return _denied_response("request_not_found")
    estatus = req["estatus"]
    info = {"inmueble": req.get("inmueble"), "propietario": req.get("propietario")}
    if estatus == access_requests.APROBADA:
        record = req["autorizacion"]
        first = not req.get("entregada")
        if first:
            # Libro mayor local: si vuelve hoy, entra directo por nombre
            invitations.upsert_record(record)
            access_requests.mark_delivered(req)
        nombre = record.get("nombre") or "Visitante"
        return _approved_response(
            record, background_tasks,
            reply=f"¡El residente aprobó su visita, {nombre}! Abriendo el portón.",
            # RF-14 una sola vez; la autorización simulada no existe en Soft-IA
            register=first and not str(record.get("id", "")).startswith("mock-"),
        )
    if estatus == access_requests.RECHAZADA:
        return _denied_response("owner_rejected", info)
    if estatus == access_requests.EXPIRADA:
        return _denied_response("owner_no_answer", info)
    if estatus == access_requests.CANCELADA:
        return _denied_response("request_cancelled", info)
    return _pending_response(req, "Esperando la respuesta del residente.")


@app.post("/api/access-request", response_model=GateResponse)
async def create_access_request(request: AccessRequestCreate) -> GateResponse:
    """Crea una solicitud de acceso con los datos ya recogidos (Soft-IA envía el WhatsApp)."""
    try:
        data = request.model_dump()
        data["motivo"] = data.get("motivo") or ""  # opcional en la API directa
        return await _request_step(IdentifyRequest(**data, request_mode=True))
    except Exception as exc:  # noqa: BLE001
        logger.exception("Fallo en POST /api/access-request: %s", exc)
        return GateResponse(**ERROR_RESPONSE.model_dump())


@app.get("/api/access-request/{request_id}", response_model=GateResponse)
async def access_request_status(request_id: str, background_tasks: BackgroundTasks) -> GateResponse:
    """Polling del tótem mientras el visitante espera la respuesta del propietario."""
    try:
        return _request_outcome(await access_requests.refresh(request_id), background_tasks)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Fallo en GET /api/access-request: %s", exc)
        return GateResponse(**ERROR_RESPONSE.model_dump())


@app.delete("/api/access-request/{request_id}", response_model=GateResponse)
async def cancel_access_request(request_id: str, background_tasks: BackgroundTasks) -> GateResponse:
    """El visitante cancela la espera."""
    try:
        return _request_outcome(await access_requests.cancel(request_id), background_tasks)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Fallo en DELETE /api/access-request: %s", exc)
        return GateResponse(**ERROR_RESPONSE.model_dump())


@app.get("/api/dev/access-requests")
def dev_pending_requests() -> list:
    """Solo modo simulado: solicitudes pendientes (para simular al propietario)."""
    if not access_requests.is_mock():
        raise HTTPException(status_code=404)
    return access_requests.list_pending()


@app.post("/api/dev/access-request/{request_id}/respond")
def dev_owner_responds(request_id: str, body: OwnerDecision) -> dict:
    """Solo modo simulado: el propietario pulsa Aprobar/Rechazar en el WhatsApp."""
    if not access_requests.is_mock():
        raise HTTPException(status_code=404)
    if body.decision not in (access_requests.APROBADA, access_requests.RECHAZADA):
        raise HTTPException(status_code=422, detail="decision: aprobada | rechazada")
    req = access_requests.resolve_mock(request_id, body.decision)
    if not req:
        raise HTTPException(status_code=404)
    return {"id": req["id"], "estatus": req["estatus"]}


@app.post("/api/verify-cedula")
async def verify_cedula(file: UploadFile = File(...), auth_id: str = Form("")) -> dict:
    """OCR local de la cédula mostrada a la cámara. Devuelve el número detectado y si
    el nombre reconocido coincide con la autorización (si se pasa `auth_id`). Cuando
    coincide, entrega el comprobante que `/api/identify` exige para aplicar la cédula."""
    try:
        image_bytes = await file.read()
        result = ocr.extract_cedula(image_bytes)
        cedula = result.get("cedula")
        match = None
        if auth_id and not result.get("error"):
            record = invitations.find_authorization(auth_id)
            if record and record.get("nombre"):
                match = access.name_matches(record["nombre"], result.get("text", ""))
        token = cedula_proof.issue(auth_id, cedula) if (auth_id and cedula and match is True) else None
        return {"cedula": cedula, "match": match, "error": result.get("error"), "cedula_token": token}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Fallo en /api/verify-cedula: %s", exc)
        return {"cedula": None, "match": None, "error": "ocr_failed", "cedula_token": None}


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

        # 6) Lista blanca: el modelo orienta, nunca autoriza ni abre el portón. El escáner
        # de QR solo se ofrece si el visitante habló de un QR o de una invitación.
        said = [request.message] + [h.text for h in request.history if h.role != "assistant"]
        return conversation.sanitize(result, allow_qr=conversation.mentions_qr(said))

    except Exception as exc:  # noqa: BLE001 - degradar con gracia ante fallo del LLM/RAG
        logger.exception("Fallo en /api/verify: %s", exc)
        return ERROR_RESPONSE


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=config.PORT, reload=True)
