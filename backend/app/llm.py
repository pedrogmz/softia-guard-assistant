"""Llamada al LLM local vía Ollama con salida estructurada (format=JSON schema)."""
from __future__ import annotations

from functools import lru_cache
from typing import List

from ollama import Client

from . import config
from .schemas import VERIFY_JSON_SCHEMA, VerifyResponse


@lru_cache(maxsize=1)
def _client() -> Client:
    return Client(host=config.OLLAMA_HOST)


def generate(messages: List[dict]) -> VerifyResponse:
    """Pide al modelo una respuesta que valida contra VerifyResponse.
    `format=VERIFY_JSON_SCHEMA` fuerza a Ollama a emitir JSON conforme al schema."""
    response = _client().chat(
        model=config.LLM_MODEL,
        messages=messages,
        format=VERIFY_JSON_SCHEMA,
        options={
            "temperature": 0.2,  # decisiones de seguridad: baja creatividad
            "num_ctx": 4096,
        },
    )
    content = response["message"]["content"]
    # El schema garantiza JSON válido; Pydantic valida enums y campos requeridos.
    return VerifyResponse.model_validate_json(content)
