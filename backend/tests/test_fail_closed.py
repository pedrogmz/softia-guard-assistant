"""Historia 1 — ningún fallo abre el portón (principio IV). Cada prueba provoca una ruta
de fallo del catálogo `specs/001-backend-fail-closed-tests/contracts/failure-routes.md`.

R22 (Soft-IA no responde al crear la solicitud) lo cubre
`test_access_requests.py::test_softia_unreachable_denies`.
"""
import json

import pytest

from app import access, access_requests, config, ocr, rag, softia, stt

from .conftest import reload_data
from .helpers import assert_authorized, assert_not_authorized, identify, make_qr, verify, verify_qr

# La función real, antes de que el fixture `client` la sustituya por un doble
REAL_RETRIEVE_CONTEXT = rag.retrieve_context

VISITOR = {"nombre": "Juan Nuevo", "cedula": "12345678", "telefono": "04141234567"}


def boom(*_args, **_kwargs):
    raise RuntimeError("fallo provocado")


async def aboom(*_args, **_kwargs):
    raise ConnectionError("sin red")


def assert_error(resp: dict) -> None:
    assert_not_authorized(resp)
    assert resp["status"] == "ERROR" and resp["action"] == "show_error", resp


def softia_real(monkeypatch):
    """Sale del modo simulado: las solicitudes pasan por el cliente de Soft-IA."""
    monkeypatch.setattr(config, "SOFTIA_SOLICITUD_MOCK", False)
    monkeypatch.setattr(config, "SOFTIA_ENABLED", True)
    monkeypatch.setattr(config, "CONDOMINIO_ID", "3304")


# --- Canal de conversación: POST /api/verify ---------------------------------------

def test_r01_llm_unavailable(client, fake_llm):
    """R01 · US1-AS1: el modelo de lenguaje no responde."""
    fake_llm(raises=ConnectionError("Ollama caído"))
    assert_error(verify(client))


@pytest.mark.parametrize("content", ["esto no es JSON", "", '{"status": "IDENTIFYING", "action": "none"}', "[1, 2]"])
def test_r02_llm_unreadable_reply(client, fake_ollama, content):
    """R02 · US1-AS2: JSON ilegible o sin `reply`."""
    fake_ollama(content)
    assert_error(verify(client))


def test_r04_knowledge_base_raises(client, fake_llm, monkeypatch):
    """R04 · US1-AS3: la consulta a la base de conocimiento lanza una excepción."""
    fake_llm(status="IDENTIFYING", action="none")
    monkeypatch.setattr(rag, "retrieve_context", boom)
    assert_error(verify(client))


def test_r04_knowledge_base_missing(tmp_path, monkeypatch):
    """R04 · US1-AS3: sin índice vectorial, la recuperación real devuelve contexto vacío
    en lugar de fallar."""
    monkeypatch.setattr(config, "CHROMA_DIR", tmp_path / "chroma_vacio")
    rag._client.cache_clear()
    try:
        assert REAL_RETRIEVE_CONTEXT("políticas de visita") == []
    finally:
        rag._client.cache_clear()


@pytest.mark.parametrize("content", [None, "{ esto no cierra"])
def test_r05_apartments_missing_or_corrupt(client, fake_llm, content):
    """R05 · US1-AS6: `apartments.json` ausente o dañado."""
    fake_llm(status="IDENTIFYING", action="none")
    if content is None:
        config.APARTMENTS_FILE.unlink()
    else:
        config.APARTMENTS_FILE.write_text(content, encoding="utf-8")
    reload_data()
    assert_error(verify(client))


# --- Identificación por QR: POST /api/verify-qr -------------------------------------

@pytest.mark.parametrize("code", ["", "   ", "no-es-un-qr-%%%", "https://softia.example/x?d=@@@", "https://softia.example/sin-payload"])
def test_r11_unreadable_qr(client, code):
    """R11 · caso límite: QR vacío, ilegible o no base64."""
    resp = verify_qr(client, code)
    assert_not_authorized(resp)
    assert resp["status"] == "DENIED"


def test_r13_invitations_missing_qr(client):
    """R13 · US1-AS6: sin libro mayor, un QR antes válido no abre."""
    assert_authorized(verify_qr(client, make_qr("20")))  # control
    config.INVITATIONS_FILE.unlink()
    reload_data()
    resp = verify_qr(client, make_qr("20"))
    assert_not_authorized(resp)
    assert resp["status"] == "DENIED"


def test_r14_invitations_corrupt_qr(client):
    """R14 · US1-AS6: libro mayor dañado."""
    config.INVITATIONS_FILE.write_text("{ dañado", encoding="utf-8")
    reload_data()
    assert_error(verify_qr(client, make_qr("20")))


def test_r15_unexpected_error_qr(client, monkeypatch):
    """R15 · US1-AS7: excepción inesperada al evaluar un QR válido."""
    monkeypatch.setattr(access, "evaluate", boom)
    assert_error(verify_qr(client, make_qr("20")))


# --- Identificación por nombre: POST /api/identify ----------------------------------

def test_r17_invitations_missing_identify(client):
    """R17 · US1-AS6: sin libro mayor, quien antes entraba por nombre pasa a la solicitud."""
    assert_authorized(identify(client, nombre="Marta Vigente"))  # control
    config.INVITATIONS_FILE.unlink()
    reload_data()
    resp = identify(client, nombre="Marta Vigente")
    assert_not_authorized(resp)
    assert resp["status"] == "NEED_INFO" and resp["request_mode"] is True


def test_r18_invitations_corrupt_identify(client):
    """R18 · US1-AS6: libro mayor dañado."""
    config.INVITATIONS_FILE.write_text("{ dañado", encoding="utf-8")
    reload_data()
    assert_error(identify(client, nombre="Marta Vigente"))


def test_r19_softia_update_fails_for_banned(client, monkeypatch):
    """R19 · US1-AS4: falla la actualización en Soft-IA de una autorización vetada."""
    monkeypatch.setattr(config, "SOFTIA_ENABLED", True)
    monkeypatch.setattr(config, "CONDOMINIO_ID", "3304")
    monkeypatch.setattr(softia, "update_autorizacion", aboom)
    resp = identify(client, auth_id="31", telefono="04140000000")
    assert_not_authorized(resp)
    assert resp["status"] == "DENIED" and not resp["request_mode"]


def test_r20_unexpected_error_identify(client, monkeypatch):
    """R20 · US1-AS7: excepción inesperada al resolver el nombre."""
    monkeypatch.setattr(access, "resolve_by_name", boom)
    assert_error(identify(client, nombre="Marta Vigente"))


# --- Solicitud de acceso: /api/access-request ---------------------------------------

def test_r23_softia_fails_on_status_poll(client, monkeypatch):
    """R23 · US1-AS4: Soft-IA falla al consultar el estado de la solicitud."""
    softia_real(monkeypatch)
    monkeypatch.setattr(config, "ACCESS_REQUEST_POLL_MIN_S", 0)

    async def created(*_):
        return {"idsolicitud": 77}

    monkeypatch.setattr(softia, "create_solicitud", created)
    monkeypatch.setattr(softia, "get_solicitud", aboom)
    resp = identify(client, request_mode=True, apartment="F-1", motivo="", **VISITOR)
    assert resp["action"] == "await_owner"
    polled = client.get(f"/api/access-request/{resp['request_id']}").json()
    assert_not_authorized(polled)
    assert polled["status"] == "PENDING_CONFIRMATION"


def test_r23_unexpected_error_on_status_poll(client, monkeypatch):
    """R23 · US1-AS7: excepción inesperada al refrescar la solicitud."""
    monkeypatch.setattr(access_requests, "refresh", aboom)
    assert_error(client.get("/api/access-request/cualquiera").json())


def test_r24_unknown_request_id(client):
    """R24 · US1-AS7: `request_id` inexistente."""
    for resp in (client.get("/api/access-request/no-existe").json(),
                 client.delete("/api/access-request/no-existe").json()):
        assert_not_authorized(resp)
        assert resp["status"] == "DENIED"


def test_r25_unexpected_error_on_cancel(client, monkeypatch):
    """R25 · US1-AS7: excepción inesperada al cancelar."""
    monkeypatch.setattr(access_requests, "cancel", aboom)
    assert_error(client.delete("/api/access-request/cualquiera").json())


# --- Voz y cédula -------------------------------------------------------------------

def test_r26_transcription_fails(client, monkeypatch):
    """R26 · US1-AS5: falla la transcripción de voz."""
    monkeypatch.setattr(stt, "transcribe", boom)
    resp = client.post("/api/transcribe", files={"file": ("clip.webm", b"audio", "audio/webm")}).json()
    assert resp == {"text": "", "error": "transcription_failed"}


@pytest.mark.parametrize("failure", ["raises", "error"])
def test_r27_id_card_reading_fails(client, monkeypatch, failure):
    """R27 · US1-AS5: falla la lectura de la cédula; no hay número, coincidencia ni comprobante."""
    if failure == "raises":
        monkeypatch.setattr(ocr, "extract_cedula", boom)
    else:
        monkeypatch.setattr(ocr, "extract_cedula", lambda _b: {"text": "", "cedula": None, "error": "ilegible"})
    resp = client.post(
        "/api/verify-cedula", files={"file": ("cedula.jpg", b"img", "image/jpeg")}, data={"auth_id": "21"}
    ).json()
    assert resp["cedula"] is None and resp["match"] is None and resp["error"]
    assert not resp.get("cedula_token")
    # La autorización sin cédula sigue sin poder completarse
    assert_not_authorized(identify(client, auth_id="21"))


# --- Fallos combinados y posteriores a la decisión ----------------------------------

def test_r28_llm_and_softia_down(client, fake_llm, monkeypatch):
    """R28 · caso límite: modelo de lenguaje y Soft-IA caídos a la vez."""
    softia_real(monkeypatch)
    fake_llm(raises=ConnectionError("Ollama caído"))
    monkeypatch.setattr(softia, "create_solicitud", aboom)
    monkeypatch.setattr(softia, "update_autorizacion", aboom)
    assert_not_authorized(verify(client))
    assert_not_authorized(verify_qr(client, make_qr("999")))
    assert_not_authorized(identify(client, nombre="Juan Nuevo"))
    resp = identify(client, request_mode=True, apartment="F-1", motivo="", **VISITOR)
    assert_not_authorized(resp)
    assert resp["status"] == "DENIED"
    assert_not_authorized(client.post("/api/access-request", json={"apartment": "F-1", **VISITOR}).json())


def test_r29_visit_log_fails_after_decision(client, monkeypatch):
    """R29 · caso límite: falla el registro de la visita tras autorizar; se encola (RF-14) y
    no se autoriza a quien no debía."""
    monkeypatch.setattr(config, "SOFTIA_ENABLED", True)
    monkeypatch.setattr(config, "CONDOMINIO_ID", "3304")
    monkeypatch.setattr(softia, "register_visita", aboom)
    assert_authorized(verify_qr(client, make_qr("20")))
    pending = json.loads(config.PENDING_VISITAS_FILE.read_text(encoding="utf-8"))
    assert [p["body"]["idvisita"] for p in pending] == [20]
    banned = verify_qr(client, make_qr("31"))
    assert_not_authorized(banned)
    assert len(json.loads(config.PENDING_VISITAS_FILE.read_text(encoding="utf-8"))) == 1
