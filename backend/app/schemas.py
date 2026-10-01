"""Modelos Pydantic. Reproducen exactamente el contrato del frontend
(frontend/src/App.tsx) y el schema del antiguo backend Gemini (server.ts)."""
from enum import Enum
from typing import List, Literal, Optional

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
    # Solicitud de acceso al propietario (visitante sin autorización vigente)
    request_mode: bool = False
    motivo: Optional[str] = None
    # Comprobante de /api/verify-cedula: sin él, `cedula` no completa una autorización
    cedula_token: Optional[str] = None


class AccessRequestCreate(BaseModel):
    """Datos del visitante para solicitar autorización al propietario por WhatsApp."""
    apartment: str
    nombre: str
    cedula: str
    telefono: str
    motivo: Optional[str] = None


class OwnerDecision(BaseModel):
    """Solo modo simulado: respuesta del propietario al WhatsApp."""
    decision: str  # "aprobada" | "rechazada"


class Status(str, Enum):
    APPROVED = "APPROVED"
    PENDING_CONFIRMATION = "PENDING_CONFIRMATION"
    DENIED = "DENIED"
    IDENTIFYING = "IDENTIFYING"
    NEED_INFO = "NEED_INFO"
    ERROR = "ERROR"


class Action(str, Enum):
    open_gate = "open_gate"
    show_qr_scanner = "show_qr_scanner"
    collect_info = "collect_info"
    show_id_scanner = "show_id_scanner"
    await_owner = "await_owner"
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


class ModelReply(BaseModel):
    """Respuesta del modelo de lenguaje leída de forma tolerante: `status` y `action`
    llegan como texto libre y los decide `conversation.sanitize` (lista blanca). Solo
    un JSON ilegible o sin `reply` es un error."""
    reply: str
    apartment: Optional[str] = None
    status: str = ""
    owner: Optional[str] = None
    action: str = ""
    assistant_animation: str = ""


class GateResponse(VerifyResponse):
    """Respuesta de la compuerta de autorización. Amplía VerifyResponse con los
    datos que faltan por recoger y el id de la autorización en curso."""
    missing: List[str] = Field(default_factory=list)
    auth_id: Optional[str] = None
    # Solicitud de acceso al propietario (WhatsApp vía Soft-IA)
    request_mode: bool = False
    request_id: Optional[str] = None
    expires_in: Optional[int] = None


class _ConversationSchema(BaseModel):
    """Lo único que se le permite emitir al modelo: el canal de conversación orienta,
    no autoriza (ver `conversation.ALLOWED`)."""
    reply: str
    apartment: Optional[str] = None
    status: Literal["IDENTIFYING", "PENDING_CONFIRMATION", "DENIED", "ERROR"]
    owner: Optional[str] = None
    action: Literal["none", "collect_info", "show_qr_scanner", "show_error"]
    assistant_animation: Literal["talking", "scanning", "idle", "denied"]


# JSON Schema que se pasa a Ollama (format=...) para forzar salida estructurada.
# Se deriva del modelo Pydantic para mantener una sola fuente de verdad.
CONVERSATION_JSON_SCHEMA = _ConversationSchema.model_json_schema()
