"""Modelos Pydantic. Reproducen exactamente el contrato del frontend
(frontend/src/App.tsx) y el schema del antiguo backend Gemini (server.ts)."""
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class HistoryItem(BaseModel):
    # El frontend envía {role, text} (no {role, content}); ver App.tsx:21-24
    role: str
    text: str


class VerifyRequest(BaseModel):
    message: str = ""
    history: List[HistoryItem] = Field(default_factory=list)
    currentAptInput: Optional[str] = ""


class QRVerifyRequest(BaseModel):
    # Texto decodificado del código QR en el navegador
    code: str = ""


class IdentifyRequest(BaseModel):
    """Identificación por nombre y recolección de datos faltantes (por voz o formulario)."""
    nombre: Optional[str] = None
    cedula: Optional[str] = None
    telefono: Optional[str] = None
    apartment: Optional[str] = None
    # Continuación del diálogo: id de la autorización ya identificada
    auth_id: Optional[str] = None


class Status(str, Enum):
    APPROVED = "APPROVED"
    PENDING_CONFIRMATION = "PENDING_CONFIRMATION"
    DENIED = "DENIED"
    IDENTIFYING = "IDENTIFYING"
    NEED_INFO = "NEED_INFO"
    ERROR = "ERROR"


class Action(str, Enum):
    open_gate = "open_gate"
    ring_bell = "ring_bell"
    show_qr_scanner = "show_qr_scanner"
    collect_info = "collect_info"
    show_id_scanner = "show_id_scanner"
    none = "none"
    show_error = "show_error"


class Animation(str, Enum):
    talking = "talking"
    scanning = "scanning"
    idle = "idle"
    success = "success"
    denied = "denied"


class VerifyResponse(BaseModel):
    reply: str
    apartment: Optional[str] = None
    status: Status
    owner: Optional[str] = None
    action: Action
    assistant_animation: Animation


class GateResponse(VerifyResponse):
    """Respuesta de la compuerta de autorización. Amplía VerifyResponse con los
    datos que faltan por recoger y el id de la autorización en curso."""
    missing: List[str] = Field(default_factory=list)
    auth_id: Optional[str] = None


# JSON Schema que se pasa a Ollama (format=...) para forzar salida estructurada.
# Se deriva del modelo Pydantic para mantener una sola fuente de verdad.
VERIFY_JSON_SCHEMA = VerifyResponse.model_json_schema()
