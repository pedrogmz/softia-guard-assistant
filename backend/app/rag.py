"""Capa RAG: acceso a los datos de apartamentos (lookup exacto) y recuperación
semántica de políticas/procedimientos desde ChromaDB (embeddings vía Ollama).

El vector store se construye con `python -m app.ingest`. Aquí solo se consulta.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import List, Optional

import chromadb
from chromadb.utils import embedding_functions

from . import config


# --------------------------------------------------------------------------- #
# Apartamentos: fuente de verdad estructurada (lookup exacto, no vectorial)
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=1)
def load_apartments() -> List[dict]:
    with open(config.APARTMENTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# Patrón de apartamento: dígito(s) + torre A/B, ej. "2B", "12a"
_APT_RE = re.compile(r"\b(\d{1,2}\s*[AB])\b", re.IGNORECASE)


def _normalize_apt(value: str) -> str:
    return re.sub(r"\s+", "", value).upper()


def find_apartment(current_apt_input: Optional[str], message: str) -> Optional[dict]:
    """Resuelve el apartamento por (1) el teclado numérico, (2) un patrón NNL en
    el mensaje, o (3) el nombre del propietario mencionado. Devuelve el registro
    o None si no se identifica."""
    apartments = load_apartments()
    by_id = {a["apt"].upper(): a for a in apartments}

    # 1) Entrada explícita del teclado numérico
    if current_apt_input:
        apt = by_id.get(_normalize_apt(current_apt_input))
        if apt:
            return apt

    # 2) Patrón "2B" dentro del mensaje hablado/escrito
    match = _APT_RE.search(message or "")
    if match:
        apt = by_id.get(_normalize_apt(match.group(1)))
        if apt:
            return apt

    # 3) Nombre del propietario (o nombre de pila) mencionado en el mensaje
    msg_lower = (message or "").lower()
    for a in apartments:
        owner = a["owner"].lower()
        if owner in msg_lower:
            return a
        first_name = owner.split()[0]
        if len(first_name) > 3 and re.search(rf"\b{re.escape(first_name)}\b", msg_lower):
            return a

    return None


# --------------------------------------------------------------------------- #
# Recuperación semántica de políticas/procedimientos desde ChromaDB
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=1)
def _embedding_function():
    return embedding_functions.OllamaEmbeddingFunction(
        url=f"{config.OLLAMA_HOST}/api/embeddings",
        model_name=config.EMBED_MODEL,
    )


@lru_cache(maxsize=1)
def _client() -> chromadb.ClientAPI:
    config.CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(config.CHROMA_DIR))


def get_collection(create: bool = False):
    """Devuelve (o crea) la colección de conocimiento con su función de embeddings."""
    client = _client()
    kwargs = dict(name=config.COLLECTION_POLICIES, embedding_function=_embedding_function())
    if create:
        return client.get_or_create_collection(**kwargs)
    return client.get_collection(**kwargs)


def retrieve_context(query: str, k: int = config.RAG_TOP_K) -> List[str]:
    """Recupera los k fragmentos de conocimiento más relevantes para la consulta.
    Devuelve lista de textos; lista vacía si el store no existe o falla."""
    if not (query or "").strip():
        return []
    try:
        collection = get_collection(create=False)
        result = collection.query(query_texts=[query], n_results=k)
        docs = result.get("documents") or [[]]
        return docs[0]
    except Exception:
        # Si el vector store aún no está construido, seguimos sin contexto RAG.
        return []
