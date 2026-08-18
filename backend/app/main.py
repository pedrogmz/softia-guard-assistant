"""API FastAPI del backend local. Expone el mismo contrato que el frontend ya
consume (POST /api/verify), pero resuelto con LLM local (Ollama) + RAG (Chroma).
No genera audio: la voz (TTS/STT) la maneja el navegador."""
from __future__ import annotations

import logging

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from . import config, llm, prompt, rag, stt
from .schemas import Action, Animation, Status, VerifyRequest, VerifyResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("guard-backend")

app = FastAPI(title="SoftiaGuard - Vigilante Virtual (backend local)")

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


@app.get("/api/apartments")
def list_apartments() -> list:
    """Paridad con el backend original (server.ts:127). El frontend actual no lo usa."""
    return rag.load_apartments()


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
