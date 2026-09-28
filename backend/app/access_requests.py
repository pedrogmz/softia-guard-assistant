"""Solicitudes de acceso al propietario por WhatsApp, vía Soft-IA (RF-20..23).

Cuando un visitante no tiene autorización vigente, el tótem recoge sus datos y crea
una solicitud. **Soft-IA** envía el WhatsApp al propietario (botones Aprobar /
Rechazar) y, si aprueba, crea una autorización de un día. Aquí se guarda el estado
de las solicitudes en curso (`data/access_requests.json`) mientras el visitante
espera, con un tiempo límite.

A diferencia del registro de visitas (RF-14), **no hay cola de reintento**: si
Soft-IA no está disponible, no se puede contactar al residente y se deniega.

Modo simulado (`SOFTIA_SOLICITUD_MOCK=true`, por defecto): no se llama a Soft-IA; la
respuesta del propietario se simula con `resolve_mock` (endpoint /api/dev/...).
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
import time
import uuid
from datetime import date
from typing import Optional

from . import config, softia, sync

logger = logging.getLogger("guard-backend.access_requests")

PENDIENTE = "pendiente"
APROBADA = "aprobada"
RECHAZADA = "rechazada"
EXPIRADA = "expirada"
CANCELADA = "cancelada"
FINAL = {APROBADA, RECHAZADA, EXPIRADA, CANCELADA}

# Las solicitudes cerradas se conservan un día (diagnóstico) y luego se purgan
_KEEP_CLOSED_S = 24 * 3600


def is_mock() -> bool:
    """Simulado si se pide explícitamente o si no hay integración con Soft-IA."""
    return config.SOFTIA_SOLICITUD_MOCK or not (config.SOFTIA_ENABLED and config.CONDOMINIO_ID)


def _load() -> dict:
    try:
        with open(config.ACCESS_REQUESTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (FileNotFoundError, ValueError, OSError):
        return {}


def _save(items: dict) -> None:
    now = time.time()
    items = {
        k: v for k, v in items.items()
        if v.get("estatus") not in FINAL or now - v.get("creada", now) < _KEEP_CLOSED_S
    }
    path = config.ACCESS_REQUESTS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def _put(req: dict) -> None:
    items = _load()
    items[req["id"]] = req
    _save(items)


def get(request_id: str) -> Optional[dict]:
    return _load().get(str(request_id))


def list_pending() -> list[dict]:
    return [r for r in _load().values() if r.get("estatus") == PENDIENTE]


def expires_in(req: dict) -> int:
    return max(0, int(req["expira"] - time.time()))


async def create(data: dict, apartment: dict) -> dict:
    """Crea la solicitud y (salvo en modo simulado) la envía a Soft-IA, que dispara el
    WhatsApp al propietario. Lanza si Soft-IA falla: el llamador deniega."""
    now = time.time()
    req = {
        "id": uuid.uuid4().hex[:12],
        "softia_id": None,
        "estatus": PENDIENTE,
        "datos": {
            "nombre": data["nombre"],
            "cedula": str(data["cedula"]),
            "telefono": str(data["telefono"]),
            "motivo": data.get("motivo") or "",
        },
        "inmueble": apartment.get("apt"),
        "propietario": apartment.get("owner"),
        "idpropietario": apartment.get("idpropietario"),
        "creada": now,
        "expira": now + config.ACCESS_REQUEST_TIMEOUT_S,
        "ultima_consulta": now,
        "autorizacion": None,
        "entregada": False,
    }
    if not is_mock():
        body = {
            "idpropietario": _to_int(req["idpropietario"]),
            "inmueble": req["inmueble"],
            **req["datos"],
            "expira_en": config.ACCESS_REQUEST_TIMEOUT_S,
        }
        resp = await softia.create_solicitud(config.CONDOMINIO_ID, body)
        sol_id = (resp or {}).get("idsolicitud", (resp or {}).get("id"))
        if sol_id is None:
            raise softia.SoftIAError("Soft-IA no devolvió el idsolicitud")
        req["softia_id"] = str(sol_id)
    else:
        logger.info(
            "[SIMULADO] WhatsApp al propietario de %s: %s (C.I. %s, tel. %s) solicita acceso. Motivo: %s",
            req["inmueble"], req["datos"]["nombre"], req["datos"]["cedula"],
            req["datos"]["telefono"], req["datos"]["motivo"] or "-",
        )
    _put(req)
    return req


async def refresh(request_id: str) -> Optional[dict]:
    """Estado actual de la solicitud: vence por tiempo y, fuera del modo simulado,
    consulta a Soft-IA como máximo cada ACCESS_REQUEST_POLL_MIN_S segundos."""
    req = get(request_id)
    if not req or req["estatus"] in FINAL:
        return req
    now = time.time()
    if now >= req["expira"]:
        req["estatus"] = EXPIRADA
        _put(req)
        await _notify_cancel(req)
        return req
    if not is_mock() and now - req.get("ultima_consulta", 0) >= config.ACCESS_REQUEST_POLL_MIN_S:
        req["ultima_consulta"] = now
        try:
            resp = await softia.get_solicitud(config.CONDOMINIO_ID, req["softia_id"])
            estatus = str((resp or {}).get("estatus", PENDIENTE)).lower()
            if estatus == APROBADA:
                auth = (resp or {}).get("autorizacion")
                if not auth:
                    raise softia.SoftIAError("Solicitud aprobada sin autorización")
                req["autorizacion"] = _from_softia(auth, req)
                req["estatus"] = APROBADA
            elif estatus in FINAL:
                req["estatus"] = estatus
        except Exception as exc:  # noqa: BLE001 - se reintenta en la siguiente consulta
            logger.warning("No se pudo consultar la solicitud %s en Soft-IA: %s", req["id"], exc)
        _put(req)
    return req


async def cancel(request_id: str) -> Optional[dict]:
    """El visitante cancela la espera."""
    req = get(request_id)
    if not req or req["estatus"] in FINAL:
        return req
    req["estatus"] = CANCELADA
    _put(req)
    await _notify_cancel(req)
    return req


def mark_delivered(req: dict) -> None:
    """La aprobación ya abrió el portón y registró la visita: no repetir."""
    req["entregada"] = True
    _put(req)


def resolve_mock(request_id: str, decision: str) -> Optional[dict]:
    """Solo modo simulado: el propietario pulsa Aprobar/Rechazar en el WhatsApp."""
    req = get(request_id)
    if not req or req["estatus"] != PENDIENTE:
        return req
    if decision == APROBADA:
        req["autorizacion"] = _day_authorization(req, f"mock-{req['id']}")
        req["estatus"] = APROBADA
    else:
        req["estatus"] = RECHAZADA
    _put(req)
    return req


async def _notify_cancel(req: dict) -> None:
    if is_mock() or not req.get("softia_id"):
        return
    try:
        await softia.cancel_solicitud(config.CONDOMINIO_ID, req["softia_id"])
    except Exception as exc:  # noqa: BLE001 - best-effort
        logger.warning("No se pudo cancelar la solicitud %s en Soft-IA: %s", req["id"], exc)


def _day_authorization(req: dict, auth_id: str) -> dict:
    """Autorización de un día en el formato del libro mayor (invitations.json)."""
    return {
        "id": auth_id,
        "nombre": req["datos"]["nombre"],
        "cedula": req["datos"]["cedula"],
        "idcondominios": str(config.CONDOMINIO_ID or ""),
        "inmueble": req["inmueble"],
        "propietario": req["propietario"],
        "idpropietario": req.get("idpropietario"),
        "autorizado_hasta": date.today().isoformat(),
        "estatus": "activo",
        "vetado": 0,
        "telefono": req["datos"]["telefono"],
    }


def _from_softia(auth: dict, req: dict) -> dict:
    """Autorización devuelta por Soft-IA -> formato del libro mayor."""
    record = sync.map_autorizaciones([auth], {})[0]
    record["inmueble"] = record.get("inmueble") or req["inmueble"]
    record["propietario"] = record.get("propietario") or req["propietario"]
    record["idpropietario"] = record.get("idpropietario") or req.get("idpropietario")
    return record


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return value
