"""Compuerta de autorización: resuelve una autorización (por nombre), detecta los
datos faltantes {nombre, cédula, teléfono} y decide si se puede autorizar el acceso.

Reutilizada por el flujo de QR (`/api/verify-qr`) y el de voz/nombre (`/api/identify`).
La decisión final de vigencia/veto se delega en `invitations.check_state`.
"""
from __future__ import annotations

import re
import unicodedata
from typing import List, Optional, Tuple

from . import invitations, rag

# Datos mínimos necesarios antes de autorizar
REQUIRED = ("nombre", "cedula", "telefono")

# Datos para una solicitud de acceso al propietario (visitante sin autorización).
# `motivo` es opcional: se pregunta una vez (None = aún no preguntado).
REQUEST_FIELDS = ("apartment", "nombre", "cedula", "telefono")


def _norm(value) -> str:
    """Minúsculas, sin acentos, espacios colapsados."""
    text = str(value or "")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", text).strip().lower()


def _digits(value) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _is_empty(value) -> bool:
    return value is None or str(value).strip() == ""


def missing_fields(record: dict) -> List[str]:
    """Campos requeridos vacíos en la autorización."""
    return [field for field in REQUIRED if _is_empty(record.get(field))]


def name_matches(query: str, record_name: str) -> bool:
    """Coincidencia por tokens: todos los tokens (>=3 letras) de la consulta aparecen
    en el nombre del registro, o coinciden exactamente."""
    q = _norm(query)
    nm = _norm(record_name)
    if not q or not nm:
        return False
    if q == nm:
        return True
    tokens = [t for t in q.split() if len(t) >= 3]
    return bool(tokens) and all(t in nm for t in tokens)


def resolve_by_name(
    nombre: Optional[str], cedula: Optional[str] = None, apartment: Optional[str] = None
) -> Tuple[str, object]:
    """Devuelve ("found", record) | ("ambiguous", [records]) | ("not_found", None)."""
    if _is_empty(nombre):
        return ("not_found", None)

    candidates = [r for r in invitations.load_invitations() if name_matches(nombre, r.get("nombre"))]

    # Desambiguar: primero por cédula, luego por apartamento
    if len(candidates) > 1 and not _is_empty(cedula):
        by_cedula = [r for r in candidates if _digits(r.get("cedula")) == _digits(cedula)]
        if by_cedula:
            candidates = by_cedula
    if len(candidates) > 1 and not _is_empty(apartment):
        ap = _norm(apartment)
        by_apt = [r for r in candidates if _norm(r.get("inmueble")) == ap]
        if by_apt:
            candidates = by_apt

    # Misma persona con una autorización vencida y otra vigente (p. ej. la de un día
    # creada al aprobar una solicitud): se usa la vigente.
    if len(candidates) > 1:
        valid = [r for r in candidates if invitations.check_state(r) == "ok"]
        if len(valid) == 1:
            candidates = valid

    if not candidates:
        return ("not_found", None)
    if len(candidates) == 1:
        return ("found", candidates[0])
    return ("ambiguous", candidates)


def evaluate(record: dict) -> dict:
    """Evalúa un registro ya identificado.
    Devuelve {"outcome": "need_info", "missing": [...]} |
             {"outcome": "ok"} | {"outcome": "denied", "reason": ...}."""
    miss = missing_fields(record)
    if miss:
        return {"outcome": "need_info", "missing": miss}
    reason = invitations.check_state(record)
    if reason == "ok":
        return {"outcome": "ok"}
    return {"outcome": "denied", "reason": reason}


# --- Solicitud de acceso (visitante sin autorización vigente) --------------------

# Motivos de denegación que permiten pedir autorización al propietario. Vetado y
# otro condominio se siguen denegando sin solicitud.
REQUESTABLE_REASONS = {"not_found", "expired", "inactivo"}


def missing_for_request(data: dict) -> List[str]:
    """Datos que faltan para enviar la solicitud; `motivo` al final si no se preguntó."""
    miss = [field for field in REQUEST_FIELDS if _is_empty(data.get(field))]
    if data.get("motivo") is None:
        miss.append("motivo")
    return miss


def find_destination(text: Optional[str]) -> Optional[dict]:
    """Inmueble destino por código ("F-1", "f 1", "PH2") o por nombre del propietario."""
    if _is_empty(text):
        return None
    key = re.sub(r"[^0-9a-z]", "", _norm(text))
    for apt in rag.load_apartments():
        if re.sub(r"[^0-9a-z]", "", _norm(apt.get("apt"))) == key:
            return apt
    return rag.find_apartment(None, str(text))


def do_not_disturb(apartment: dict) -> bool:
    return "molestar" in _norm(apartment.get("status"))
