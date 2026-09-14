"""Parseo del código QR de invitación generado por Soft-IA.

El QR contiene una URL con la forma:
    https://<dominio>/app/control/detalles_visitante/<id_b64>?d=<json_b64>
donde `d` es un JSON (base64) con los datos de la visita (incluye el `id` de la
autorización). Este módulo SOLO extrae ese payload; la DECISIÓN de acceso se toma
en `invitations.py` según el estado real de la autorización (el QR no es la fuente
de verdad, ver nota de seguridad en docs/requirements.md).
"""
from __future__ import annotations

import base64
import binascii
import json
from typing import Optional
from urllib.parse import parse_qs, urlparse


def _b64_decode(value: str) -> bytes:
    """Decodifica base64 estándar o url-safe, con o sin relleno."""
    s = value.strip().replace("-", "+").replace("_", "/")
    s += "=" * (-len(s) % 4)
    return base64.b64decode(s)


def _extract_payload(code: str) -> Optional[str]:
    """Obtiene el parámetro `d` (JSON en base64) de la URL escaneada. Si el código
    no es una URL, se asume que ya es el propio payload base64."""
    code = (code or "").strip()
    if not code:
        return None
    if "?" in code or "://" in code or code.startswith("/"):
        query = parse_qs(urlparse(code).query)
        if query.get("d"):
            return query["d"][0]
        return None
    return code


def parse_qr(code: str) -> Optional[dict]:
    """Extrae el JSON de la visita del QR. Devuelve el dict del payload (que incluye
    `id`) o None si el código no se puede leer."""
    payload = _extract_payload(code)
    if not payload:
        return None
    try:
        data = json.loads(_b64_decode(payload).decode("utf-8"))
    except (binascii.Error, ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None
