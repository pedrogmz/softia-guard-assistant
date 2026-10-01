"""Historia 2 — la decisión sigue el estado real de la autorización (principio V).
Tabla «Estado → decisión» de `specs/001-backend-fail-closed-tests/data-model.md`.

Ya cubierto en `test_access_requests.py` y no duplicado aquí: vetada por nombre
(US2-AS2, `test_banned_visitor_never_gets_a_request`), vencida que reutiliza datos
(US2-AS3, `test_expired_visitor_reuses_data`), «No Molestar» (US2-AS7,
`test_do_not_disturb`) e inexistente por nombre (`test_unknown_visitor_enters_request_mode`).
"""
import pytest

from app import access, config, invitations

from .conftest import CONDO, _inv
from .helpers import assert_authorized, assert_not_authorized, identify, make_qr, verify_qr


def assert_denied_without_request(resp: dict) -> None:
    assert_not_authorized(resp)
    assert resp["status"] == "DENIED" and not resp["request_mode"], resp


def assert_offers_request(resp: dict) -> None:
    assert_not_authorized(resp)
    assert resp["status"] == "NEED_INFO" and resp["request_mode"] is True, resp


# --- Estado → decisión, por QR y por nombre -----------------------------------------

def test_valid_authorization_opens(client):
    """US2-AS1 (control): vigente, activa, no vetada y completa."""
    assert_authorized(verify_qr(client, make_qr("20")))
    assert_authorized(identify(client, nombre="Marta Vigente"))


def test_banned_is_denied_without_request(client):
    """US2-AS2: vetada, por QR y por nombre."""
    assert_denied_without_request(verify_qr(client, make_qr("10")))
    assert_denied_without_request(identify(client, nombre="Ana Vetada"))


@pytest.mark.parametrize("auth_id, nombre", [("25", "Ines Ayer"), ("22", "Rosa Eliminada")])
def test_expired_or_inactive_never_enters_directly(client, auth_id, nombre):
    """US2-AS3: vencida o inactiva; por nombre solo queda la solicitud de acceso."""
    resp = verify_qr(client, make_qr(auth_id))
    assert_not_authorized(resp)
    assert resp["status"] == "DENIED"
    assert_offers_request(identify(client, nombre=nombre))


def test_other_condominium_is_denied(client, monkeypatch):
    """US2-AS4: autorización de otro condominio."""
    monkeypatch.setattr(config, "CONDOMINIO_ID", CONDO)
    assert_authorized(verify_qr(client, make_qr("20")))  # control: la del condominio propio abre
    assert_denied_without_request(verify_qr(client, make_qr("23")))
    assert_denied_without_request(identify(client, nombre="Oscar Otrocondo"))


def test_unknown_id_never_opens(client):
    """US2-AS5 · R12 · R21: identificador inexistente o ausente."""
    for code in (make_qr("999"), make_qr(None), make_qr("")):
        resp = verify_qr(client, code)
        assert_not_authorized(resp)
        assert resp["status"] == "DENIED"
    assert_denied_without_request(identify(client, auth_id="999"))


def test_qr_content_does_not_decide(client):
    """US2-AS6 · R16: decide el registro, no lo que diga el QR."""
    forged = make_qr("10", estatus="activo", vetado=0, autorizado_hasta="2099-12-31", nombre="Otra Persona")
    assert_denied_without_request(verify_qr(client, forged))
    forged_expired = make_qr("25", autorizado_hasta="2099-12-31")
    assert_not_authorized(verify_qr(client, forged_expired))
    # A la inversa: un QR que se declara vetado o vencido abre si el registro es válido
    assert_authorized(verify_qr(client, make_qr("20", estatus="inactivo", vetado=1, autorizado_hasta="2000-01-01")))


def test_do_not_disturb_never_creates_request(client):
    """US2-AS7: inmueble «No Molestar»; no se crea solicitud ni por la API directa."""
    resp = client.post("/api/access-request", json={
        "apartment": "1B", "nombre": "Juan Nuevo", "cedula": "12345678", "telefono": "04141234567",
    }).json()
    assert_denied_without_request(resp)
    assert not config.ACCESS_REQUESTS_FILE.exists()


# --- Casos límite sobre el estado real (check_state) --------------------------------

def state(**over) -> str:
    return invitations.check_state(_inv("99", "Caso Limite", **over))


def test_edge_expires_today_is_still_valid(client):
    """EDGE-vence-hoy: vigente durante el día de vencimiento, no al día siguiente."""
    assert_authorized(identify(client, nombre="Hugo Hoy"))
    assert_offers_request(identify(client, nombre="Ines Ayer"))


def test_edge_ban_prevails_over_everything():
    """EDGE-veto-prevalece: el veto gana a una fecha vigente y a un estatus activo."""
    assert state(vetado=1) == "vetado"
    assert state(vetado=1, autorizado_hasta="2000-01-01") == "vetado"
    assert state(vetado=1, estatus="eliminado") == "vetado"


@pytest.mark.parametrize("value", ["true", "si", "sí", 2, "x", "1", 1, True])
def test_edge_unknown_ban_value_counts_as_banned(value):
    """EDGE-campos-desconocidos (D5): solo 0, "0", False, None o vacío significan «no vetado»."""
    assert state(vetado=value) == "vetado"


@pytest.mark.parametrize("value", [0, "0", False, None, ""])
def test_edge_known_not_banned_values(value):
    """Control de D5: los valores que sí significan «no vetado»."""
    assert state(vetado=value) == "ok"


@pytest.mark.parametrize("value", ["", None, "31/12/2099", "mañana", "2099-13-45"])
def test_edge_missing_or_malformed_date_is_inactive(value):
    """EDGE-campos-ausentes (D3, D4): sin fecha válida no hay vigencia."""
    assert state(autorizado_hasta=value) == "inactivo"


@pytest.mark.parametrize("nombre", ["Lucas Sinfecha", "Nora Malfecha"])
def test_edge_bad_date_never_enters_directly(client, nombre):
    """EDGE-campos-ausentes (D3, D4), por HTTP: pasa a la solicitud, no entra."""
    assert_offers_request(identify(client, nombre=nombre))


def test_edge_unknown_ban_value_by_http(client):
    """EDGE-campos-desconocidos (D5), por HTTP."""
    assert_denied_without_request(verify_qr(client, make_qr("28")))
    assert_denied_without_request(identify(client, nombre="Tomas Vetotexto"))


@pytest.mark.parametrize("over", [{"estatus": None}, {"estatus": ""}, {"estatus": "pendiente"}])
def test_edge_missing_or_unknown_status_is_inactive(over):
    """EDGE-campos-ausentes: sin estatus «activo» no es válida."""
    assert state(**over) == "inactivo"


# --- Homónimos (D9) -----------------------------------------------------------------

def test_r36_homonyms_with_a_banned_one_are_not_auto_resolved(client):
    """R36 · EDGE-homonimos (D9): con un homónimo vetado no se elige al válido solo por nombre."""
    resp = identify(client, nombre="Raul Gemelo")
    assert_not_authorized(resp)
    assert resp["status"] == "NEED_INFO" and resp["missing"] == ["apartment"]
    assert access.resolve_by_name("Raul Gemelo")[0] == "ambiguous"


def test_homonyms_resolved_by_id_card_or_apartment(client):
    """EDGE-homonimos: al desambiguar decide el estado real de cada uno."""
    assert_authorized(identify(client, nombre="Raul Gemelo", cedula="290290"))
    assert_authorized(identify(client, nombre="Raul Gemelo", apartment="F-1"))
    assert_denied_without_request(identify(client, nombre="Raul Gemelo", cedula="300300"))
    assert_denied_without_request(identify(client, nombre="Raul Gemelo", apartment="1B"))


def test_same_person_expired_and_valid_uses_the_valid_one():
    """Control de D9: con una vencida y una vigente (sin vetadas) se usa la vigente."""
    candidates = [_inv("40", "Sara Doble", autorizado_hasta="2000-01-01"), _inv("41", "Sara Doble")]
    invitations.load_invitations.cache_clear()
    try:
        from unittest.mock import patch
        with patch.object(invitations, "load_invitations", lambda: candidates):
            outcome, record = access.resolve_by_name("Sara Doble")
    finally:
        invitations.load_invitations.cache_clear()
    assert outcome == "found" and record["id"] == "41"
