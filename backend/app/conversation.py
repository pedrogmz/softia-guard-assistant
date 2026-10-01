"""Guarda del canal de conversación (`POST /api/verify`).

El modelo de lenguaje orienta al visitante, pero **nunca autoriza**: un visitante puede
convencerlo de cualquier cosa. La decisión de abrir sale solo de las rutas que evalúan el
estado real de la autorización (`/api/verify-qr`, `/api/identify`) o de la respuesta del
propietario. Aquí se aplica una **lista blanca** a lo que el modelo devuelve; todo lo
demás, incluidos valores que no existen en el esquema, se rebaja a «identifíquese».
"""
from __future__ import annotations

import re
import unicodedata
from typing import Iterable

from .schemas import Action, Animation, ModelReply, Status, VerifyResponse

# Únicas combinaciones (status, action) que el canal de conversación puede devolver
ALLOWED = {
    (Status.IDENTIFYING, Action.none),
    (Status.IDENTIFYING, Action.collect_info),
    (Status.PENDING_CONFIRMATION, Action.show_qr_scanner),
    (Status.DENIED, Action.show_error),
    (Status.ERROR, Action.show_error),
}

FALLBACK_REPLY = (
    "Para continuar necesito verificar su autorización. Por favor, dígame su nombre "
    "completo o muestre su código QR."
)

_DEFAULT_ANIMATION = {
    Status.IDENTIFYING: Animation.talking,
    Status.PENDING_CONFIRMATION: Animation.scanning,
    Status.DENIED: Animation.denied,
    Status.ERROR: Animation.denied,
}


def _enum(enum, value):
    try:
        return enum(value)
    except ValueError:
        return None


_QR_WORDS = re.compile(r"\b(qr|codigo|codigos|invitacion)\b")


def mentions_qr(texts: Iterable[str]) -> bool:
    """True si el visitante habló de un código QR o de una invitación."""
    for text in texts:
        plain = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()
        if _QR_WORDS.search(plain):
            return True
    return False


def sanitize(raw: ModelReply, allow_qr: bool = True) -> VerifyResponse:
    """Convierte la respuesta tolerante del modelo en la respuesta al tótem.
    `allow_qr=False` (el visitante no mencionó ningún QR) rebaja también la petición de
    escanear: sin las salidas que ya no puede usar, el modelo tiende a pedir el QR a todos."""
    status, action = _enum(Status, raw.status), _enum(Action, raw.action)
    if action is Action.show_qr_scanner and not allow_qr:
        action = None
    if (status, action) not in ALLOWED or not raw.reply.strip():
        return VerifyResponse(
            reply=FALLBACK_REPLY,
            apartment=raw.apartment,
            status=Status.IDENTIFYING,
            owner=raw.owner,
            action=Action.collect_info,
            assistant_animation=Animation.talking,
        )
    animation = _enum(Animation, raw.assistant_animation)
    if animation is None or animation is Animation.success:
        animation = _DEFAULT_ANIMATION[status]
    return VerifyResponse(
        reply=raw.reply,
        apartment=raw.apartment,
        status=status,
        owner=raw.owner,
        action=action,
        assistant_animation=animation,
    )
