"""Llamada al LLM local vía Ollama con salida estructurada (format=JSON schema)."""
from __future__ import annotations

from functools import lru_cache
from typing import List

from ollama import Client

from . import config
from .schemas import CONVERSATION_JSON_SCHEMA, ModelReply


@lru_cache(maxsize=1)
def _client() -> Client:
    return Client(host=config.OLLAMA_HOST)


def generate(messages: List[dict]) -> ModelReply:
    """Pide al modelo una respuesta y la lee de forma tolerante (`ModelReply`).
    `format=CONVERSATION_JSON_SCHEMA` pide a Ollama solo los valores permitidos, pero
    quien decide qué llega al tótem es `conversation.sanitize`."""
    response = _client().chat(
        model=config.LLM_MODEL,
        messages=messages,
        format=CONVERSATION_JSON_SCHEMA,
        options={
            "temperature": 0.2,  # decisiones de seguridad: baja creatividad
            "num_ctx": 4096,
        },
    )
    content = response["message"]["content"]
    # JSON ilegible o sin `reply` lanza: el llamador responde con la contingencia.
    return ModelReply.model_validate_json(content)
