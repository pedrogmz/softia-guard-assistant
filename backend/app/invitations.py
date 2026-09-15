"""Libro mayor de autorizaciones del condominio (`data/invitations.json`).

Contiene el **estado real** de cada autorización de visita. El código QR de Soft-IA
solo aporta el `id` de una autorización; la decisión de acceso se toma con el
registro almacenado aquí, no con lo que traiga el QR (que es falsificable). En
producción, este libro mayor lo provee/ sincroniza **Soft-IA** (objetivo RF-15).
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import date
from functools import lru_cache
from typing import Optional

from . import config

# Campos del libro mayor local que se pueden actualizar tras completar datos
_LOCAL_UPDATABLE = {"cedula", "telefono", "nombre", "email", "autorizado_hasta", "estatus", "vetado"}


@lru_cache(maxsize=1)
def load_invitations() -> list[dict]:
    try:
        with open(config.INVITATIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def find_authorization(auth_id) -> Optional[dict]:
    """Busca la autorización por `id` en el libro mayor."""
    if auth_id is None or str(auth_id).strip() == "":
        return None
    for inv in load_invitations():
        if str(inv.get("id")) == str(auth_id):
            return inv
    return None


def update_record(auth_id, fields: dict) -> bool:
    """Actualiza un registro del libro mayor local (para reflejar datos completados
    sin esperar la próxima sync). Devuelve True si escribió algún cambio."""
    try:
        with open(config.INVITATIONS_FILE, "r", encoding="utf-8") as f:
            items = json.load(f)
    except (FileNotFoundError, ValueError, OSError):
        return False

    updates = {k: v for k, v in fields.items() if k in _LOCAL_UPDATABLE and v not in (None, "")}
    if not updates:
        return False

    changed = False
    for rec in items:
        if str(rec.get("id")) == str(auth_id):
            rec.update(updates)
            changed = True
            break
    if not changed:
        return False

    dir_ = config.INVITATIONS_FILE.parent
    fd, tmp = tempfile.mkstemp(dir=str(dir_), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        os.replace(tmp, config.INVITATIONS_FILE)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    load_invitations.cache_clear()
    return True


def check_state(record: dict) -> str:
    """Evalúa el estado real de la autorización almacenada.
    Devuelve: ok | wrong_condominio | vetado | inactivo | expired."""
    if config.CONDOMINIO_ID and str(record.get("idcondominios", "")) != str(config.CONDOMINIO_ID):
        return "wrong_condominio"
    if record.get("vetado") in (1, "1", True):
        return "vetado"
    if str(record.get("estatus", "")).lower() != "activo":
        return "inactivo"
    autorizado_hasta = record.get("autorizado_hasta")
    if autorizado_hasta:
        try:
            if date.today() > date.fromisoformat(str(autorizado_hasta)):
                return "expired"
        except ValueError:
            pass  # fecha mal formada: se ignora la comprobación de vigencia
    return "ok"
