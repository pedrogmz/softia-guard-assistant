"""STT local con Whisper (faster-whisper / CTranslate2). Sin servicios en la nube
en tiempo de ejecución: el modelo se descarga una sola vez y queda cacheado.

El modelo se carga de forma perezosa (lazy) en la primera transcripción para no
retrasar el arranque de la API."""
from __future__ import annotations

import io
import logging
from functools import lru_cache

from faster_whisper import WhisperModel

from . import config

logger = logging.getLogger("guard-backend.stt")


@lru_cache(maxsize=1)
def _model() -> WhisperModel:
    logger.info(
        "Cargando Whisper '%s' (device=%s, compute=%s)...",
        config.WHISPER_MODEL,
        config.WHISPER_DEVICE,
        config.WHISPER_COMPUTE_TYPE,
    )
    return WhisperModel(
        config.WHISPER_MODEL,
        device=config.WHISPER_DEVICE,
        compute_type=config.WHISPER_COMPUTE_TYPE,
    )


def transcribe(audio_bytes: bytes) -> str:
    """Transcribe un clip de audio (webm/ogg/wav/mp4...) a texto en español.
    faster-whisper decodifica el contenedor internamente (PyAV), así que no hace
    falta ffmpeg del sistema."""
    if not audio_bytes:
        return ""

    language = config.WHISPER_LANGUAGE or None
    segments, _info = _model().transcribe(
        io.BytesIO(audio_bytes),
        language=language,
        vad_filter=True,  # descarta silencios -> más rápido y limpio
        beam_size=5,
    )
    return " ".join(segment.text.strip() for segment in segments).strip()
