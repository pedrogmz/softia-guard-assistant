"""Construye (o reconstruye) el vector store de ChromaDB a partir de:
  - data/apartments.json  -> un documento por apartamento
  - knowledge/*.md        -> troceado por secciones (## ...)

Uso:
    python -m app.ingest

Requiere que Ollama esté corriendo y que el modelo de embeddings esté descargado:
    ollama pull bge-m3
"""
from __future__ import annotations

import glob
import os
import re
from typing import List, Tuple

from . import config
from .rag import _client, _embedding_function, load_apartments


def _chunk_markdown(text: str) -> List[str]:
    """Trocea un markdown por encabezados de nivel 2 (## ...). Cada sección es
    un chunk; si no hay encabezados, se devuelve el documento entero."""
    parts = re.split(r"(?=^##\s)", text, flags=re.MULTILINE)
    chunks = [p.strip() for p in parts if p.strip()]
    return chunks or [text.strip()]


def _collect_documents() -> Tuple[List[str], List[dict], List[str]]:
    documents: List[str] = []
    metadatas: List[dict] = []
    ids: List[str] = []

    # 1) Apartamentos: un documento legible por unidad
    for apt in load_apartments():
        doc = (
            f"Apartamento {apt['apt']}. Propietario: {apt['owner']}. "
            f"Estado: {apt['status']}. Notas: {apt['notes']}"
        )
        documents.append(doc)
        metadatas.append({"type": "apartment", "apt": apt["apt"], "source": "apartments.json"})
        ids.append(f"apt-{apt['apt']}")

    # 2) Políticas y procedimientos (knowledge/*.md)
    for path in sorted(glob.glob(str(config.KNOWLEDGE_DIR / "*.md"))):
        fname = os.path.basename(path)
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        for i, chunk in enumerate(_chunk_markdown(text)):
            documents.append(chunk)
            metadatas.append({"type": "policy", "source": fname})
            ids.append(f"{fname}-{i}")

    return documents, metadatas, ids


def main() -> None:
    print(f"[ingest] Ollama: {config.OLLAMA_HOST} | embeddings: {config.EMBED_MODEL}")
    print(f"[ingest] Vector store: {config.CHROMA_DIR}")

    client = _client()
    # Reconstrucción limpia: borrar la colección previa si existe
    try:
        client.delete_collection(config.COLLECTION_POLICIES)
        print(f"[ingest] Colección previa '{config.COLLECTION_POLICIES}' eliminada.")
    except Exception:
        pass

    collection = client.create_collection(
        name=config.COLLECTION_POLICIES,
        embedding_function=_embedding_function(),
    )

    documents, metadatas, ids = _collect_documents()
    print(f"[ingest] Indexando {len(documents)} documentos (apartamentos + políticas)...")
    collection.add(documents=documents, metadatas=metadatas, ids=ids)
    print(f"[ingest] Listo. {collection.count()} documentos en '{config.COLLECTION_POLICIES}'.")


if __name__ == "__main__":
    main()
