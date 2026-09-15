"""Registro de eventos de acceso en Soft-IA (RF-14), offline-first.

Cuando un acceso por QR se autoriza, se registra la visita en Soft-IA. Si Soft-IA
no responde, el evento se **encola** en `data/pending_visitas.json` y se reintenta
en el siguiente ciclo de sincronización (o vía `flush_pending`), para no perder la
auditoría durante una caída de conexión.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import List

import httpx

from . import config, softia

logger = logging.getLogger("guard-backend.events")

# Serializa las escrituras concurrentes al archivo de pendientes
_lock = asyncio.Lock()


def _is_retryable(exc: Exception) -> bool:
    """Reintentar solo ante fallos transitorios (red/5xx). Un 4xx de Soft-IA
    (vencida, no existe, vetada...) es una rechazo definitivo: no se reintenta."""
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return True  # errores de conexión/timeout/login -> transitorios


def _load_pending() -> List[dict]:
    try:
        with open(config.PENDING_VISITAS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except FileNotFoundError:
        return []
    except (ValueError, OSError):
        return []


def _save_pending(items: List[dict]) -> None:
    config.PENDING_VISITAS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(config.PENDING_VISITAS_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


async def register_or_queue(condominio_id: str, body: dict) -> None:
    """Registra la visita; si falla por red/5xx, la encola para reintentar. Un
    rechazo definitivo (4xx) se descarta (no tiene sentido reintentarlo)."""
    try:
        await softia.register_visita(condominio_id, body)
        logger.info("Visita registrada en Soft-IA (idvisita=%s)", body.get("idvisita"))
    except Exception as exc:  # noqa: BLE001
        if not _is_retryable(exc):
            logger.warning("Soft-IA rechazó la visita (idvisita=%s): %s. No se reintenta.",
                           body.get("idvisita"), exc)
            return
        logger.warning("No se pudo registrar la visita (%s). Se encola para reintento.", exc)
        async with _lock:
            pending = _load_pending()
            pending.append({"condominio_id": condominio_id, "body": body})
            _save_pending(pending)


async def flush_pending() -> dict:
    """Reintenta registrar las visitas encoladas. Conserva las que sigan fallando."""
    async with _lock:
        pending = _load_pending()
    if not pending:
        return {"flushed": 0, "pending": 0}

    remaining: List[dict] = []
    flushed = 0
    for event in pending:
        try:
            await softia.register_visita(event.get("condominio_id"), event.get("body", {}))
            flushed += 1
        except Exception as exc:  # noqa: BLE001
            if _is_retryable(exc):
                remaining.append(event)  # sigue pendiente
            else:
                logger.warning("Visita encolada rechazada por Soft-IA: %s. Se descarta.", exc)

    async with _lock:
        _save_pending(remaining)
    if flushed:
        logger.info("Visitas pendientes reenviadas: %d (quedan %d)", flushed, len(remaining))
    return {"flushed": flushed, "pending": len(remaining)}
