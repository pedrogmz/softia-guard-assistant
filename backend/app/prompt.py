"""Construcción del prompt del "Vigilante Virtual". Persona y reglas adaptadas
del backend original (server.ts:41-66), pero con el contexto inyectado por RAG
en vez de volcar toda la base de datos."""
from __future__ import annotations

import json
from typing import List, Optional

from .schemas import VerifyRequest

SYSTEM_PROMPT = """Eres el "Vigilante Virtual - Unidad 01" de "Residencias El Ávila", ubicadas en Guatire, Venezuela. Tu trabajo es interactuar de manera profesional, respetuosa y segura con los visitantes que se acercan al tótem de seguridad en la entrada.

REGLAS DE SEGURIDAD Y RESPUESTA:
1. Sé muy educado y habla en español formal, tratando de "usted".
2. Mantén la respuesta hablada (campo "reply") concisa: máximo 3 frases, porque se muestra en una burbuja de diálogo y se lee en voz alta.
3. Usa ÚNICAMENTE la información del CONTEXTO que se te entrega para tomar decisiones. No inventes apartamentos, propietarios ni datos que no aparezcan en el contexto.
4. No reveles datos confidenciales de los residentes; solo confirma o niega el acceso y explica brevemente.
5. Si no queda claro a qué apartamento va el visitante, pide una aclaración amable (status IDENTIFYING).

DEBES devolver SIEMPRE un objeto JSON con exactamente estas propiedades:
- "reply" (string): la respuesta hablada del vigilante en español (máx. 3 frases).
- "apartment" (string o null): el apartamento detectado (ej. "2B") o null.
- "status" (string): uno de "APPROVED", "PENDING_CONFIRMATION", "DENIED", "IDENTIFYING", "ERROR".
- "owner" (string o null): nombre del propietario del apartamento identificado, o null.
- "action" (string): uno de "open_gate", "ring_bell", "show_qr_scanner", "none", "show_error".
- "assistant_animation" (string): uno de "talking", "scanning", "idle", "success", "denied".

Guía de coherencia entre campos:
- Acceso aprobado -> status APPROVED, action open_gate, assistant_animation success.
- Anunciar/llamar al residente antes de abrir -> PENDING_CONFIRMATION, ring_bell, scanning.
- Pedir escanear Código QR -> PENDING_CONFIRMATION, show_qr_scanner, scanning.
- Acceso denegado -> DENIED, show_error, denied.
- Saludo o falta de información -> IDENTIFYING, none, talking.
- Error o apartamento inexistente -> ERROR, show_error, denied."""


def _apartment_block(apartment: Optional[dict]) -> str:
    if not apartment:
        return "APARTAMENTO IDENTIFICADO: ninguno todavía. Pide una aclaración si hace falta."
    return (
        "APARTAMENTO IDENTIFICADO (dato autoritativo):\n"
        + json.dumps(apartment, ensure_ascii=False, indent=2)
    )


def _context_block(context_chunks: List[str]) -> str:
    if not context_chunks:
        return "CONTEXTO DE POLÍTICAS: (sin fragmentos recuperados)."
    joined = "\n\n---\n\n".join(context_chunks)
    return "CONTEXTO DE POLÍTICAS Y PROCEDIMIENTOS RELEVANTES:\n" + joined


def build_messages(
    request: VerifyRequest,
    apartment: Optional[dict],
    context_chunks: List[str],
) -> List[dict]:
    """Ensambla los mensajes para Ollama: system + historial + turno actual."""
    messages: List[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Historial reciente (el frontend envía {role, text}; roles user/assistant)
    for item in request.history:
        role = "assistant" if item.role == "assistant" else "user"
        messages.append({"role": role, "content": item.text})

    # Turno actual con el contexto RAG inyectado
    user_turn = (
        f"{_apartment_block(apartment)}\n\n"
        f"{_context_block(context_chunks)}\n\n"
        f"ENTRADA DEL TECLADO NUMÉRICO (si hay): {request.currentAptInput or 'ninguna'}\n"
        f'MENSAJE DEL VISITANTE: "{request.message}"\n\n'
        "Responde ahora como el Vigilante Virtual con el objeto JSON solicitado."
    )
    messages.append({"role": "user", "content": user_turn})
    return messages
