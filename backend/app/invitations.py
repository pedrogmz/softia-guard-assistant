"""Libro mayor de autorizaciones del condominio (`data/invitations.json`).

Contiene el **estado real** de cada autorización de visita. El código QR de Soft-IA
solo aporta el `id` de una autorización; la decisión de acceso se toma con el
registro almacenado aquí, no con lo que traiga el QR (que es falsificable). En
producción, este libro mayor lo provee/ sincroniza **Soft-IA** (objetivo RF-15).
"""
from __future__ import annotations

import json
from datetime import date
from functools import lru_cache
from typing import Optional

from . import config


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
