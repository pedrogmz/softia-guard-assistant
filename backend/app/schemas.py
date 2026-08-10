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


class Status(str, Enum):
    APPROVED = "APPROVED"
    PENDING_CONFIRMATION = "PENDING_CONFIRMATION"
    DENIED = "DENIED"
    IDENTIFYING = "IDENTIFYING"
    ERROR = "ERROR"


class Action(str, Enum):
    open_gate = "open_gate"
    ring_bell = "ring_bell"
    show_qr_scanner = "show_qr_scanner"
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


# JSON Schema que se pasa a Ollama (format=...) para forzar salida estructurada.
# Se deriva del modelo Pydantic para mantener una sola fuente de verdad.
VERIFY_JSON_SCHEMA = VerifyResponse.model_json_schema()
