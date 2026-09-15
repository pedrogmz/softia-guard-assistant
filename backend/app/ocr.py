"""OCR local de la cédula con Tesseract (pytesseract + Pillow).

Extrae el texto de la foto de la cédula y trata de aislar un número de cédula. La
verificación del nombre se hace en el endpoint comparando el nombre de la
autorización contra el texto reconocido (ver access.name_matches).

Nota: la fiabilidad del OCR sobre cédulas reales es limitada (orientación, brillos,
tipografías); es best-effort y admite reintento.
"""
from __future__ import annotations

import io
import logging
import re

import pytesseract
from PIL import Image, ImageOps

logger = logging.getLogger("guard-backend.ocr")

# Número de cédula: 6-9 dígitos, con o sin separadores de miles
_CEDULA_RE = re.compile(r"\b\d{1,3}(?:[.\s]\d{3}){1,2}\b|\b\d{6,9}\b")


def extract_cedula(image_bytes: bytes) -> dict:
    """Devuelve {'text': <texto OCR>, 'cedula': <número|None>, 'error': <str|None>}."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = ImageOps.exif_transpose(img).convert("L")  # orienta y pasa a gris
    except Exception as exc:  # noqa: BLE001
        return {"text": "", "cedula": None, "error": f"imagen inválida: {exc}"}

    try:
        text = pytesseract.image_to_string(img, lang="spa")
    except pytesseract.TesseractNotFoundError:
        return {"text": "", "cedula": None, "error": "Tesseract no está instalado"}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Fallo de OCR: %s", exc)
        return {"text": "", "cedula": None, "error": str(exc)}

    cedula = None
    match = _CEDULA_RE.search(text)
    if match:
        cedula = re.sub(r"\D", "", match.group())

    return {"text": text, "cedula": cedula, "error": None}
