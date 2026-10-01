"""Comprobante de la verificación de cédula.

`/api/verify-cedula` lee la cédula por cámara y compara el nombre con el de la
autorización. Para que `/api/identify` no tenga que fiarse de lo que declare el tótem,
esa verificación se entrega como un comprobante firmado que liga autorización, número
de cédula y caducidad. Sin comprobante válido, una cédula no completa una autorización
(una cédula escrita a mano nunca lo tiene).

El secreto se genera al arrancar: si el backend se reinicia, los comprobantes pendientes
dejan de valer y el visitante repite la lectura.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import time
from typing import Optional

from . import config

_SECRET = secrets.token_bytes(32)


def _digits(value) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _sign(auth_id, cedula: str, exp: int) -> str:
    message = f"{auth_id}|{cedula}|{exp}".encode()
    return hmac.new(_SECRET, message, hashlib.sha256).hexdigest()


def issue(auth_id, cedula) -> str:
    """Comprobante para una cédula ya verificada contra la autorización `auth_id`."""
    exp = int(time.time()) + config.CEDULA_PROOF_TTL_S
    return f"{exp}.{_sign(auth_id, _digits(cedula), exp)}"


def is_valid(token: Optional[str], auth_id, cedula) -> bool:
    """True solo si el comprobante es íntegro, no ha caducado y corresponde a esa
    autorización y a ese número."""
    number = _digits(cedula)
    if not token or not number or auth_id is None:
        return False
    exp_text, _, signature = str(token).partition(".")
    if not exp_text.isdigit() or not signature:
        return False
    exp = int(exp_text)
    if time.time() > exp:
        return False
    return hmac.compare_digest(signature, _sign(auth_id, number, exp))
