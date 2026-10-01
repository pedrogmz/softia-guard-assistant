"""Historia 2 — la coincidencia de nombre de la cédula se exige en el backend (FR-015,
principio V). Contrato: `contracts/conversation-channel.md`, «Verificación de cédula»."""
import pytest

from app import cedula_proof, config, invitations, ocr

from .helpers import assert_authorized, assert_not_authorized, identify

CEDULA = "12345678"


def read_card(monkeypatch, text, cedula=CEDULA):
    monkeypatch.setattr(ocr, "extract_cedula", lambda _b: {"text": text, "cedula": cedula, "error": None})


def scan(client, auth_id=""):
    return client.post(
        "/api/verify-cedula", files={"file": ("cedula.jpg", b"img", "image/jpeg")}, data={"auth_id": auth_id}
    ).json()


def stored_cedula(auth_id) -> str:
    invitations.load_invitations.cache_clear()
    return invitations.find_authorization(auth_id)["cedula"]


def assert_asks_for_card(resp: dict) -> None:
    assert_not_authorized(resp)
    assert (resp["status"], resp["action"]) == ("NEED_INFO", "show_id_scanner"), resp


# --- Comprobante (unitarias) --------------------------------------------------------

def test_proof_is_valid_for_same_authorization_and_number():
    token = cedula_proof.issue("21", CEDULA)
    assert cedula_proof.is_valid(token, "21", CEDULA)
    assert cedula_proof.is_valid(token, 21, "12.345.678")  # mismo número con separadores


@pytest.mark.parametrize("token", [None, "", "abc", "123.abc", "x.y.z", "9999999999."])
def test_malformed_proof_is_rejected(token):
    assert not cedula_proof.is_valid(token, "21", CEDULA)


def test_proof_is_bound_and_expires(monkeypatch):
    """R31 · EDGE-comprobante: otra autorización, otro número, alterado o caducado."""
    token = cedula_proof.issue("21", CEDULA)
    assert not cedula_proof.is_valid(token, "20", CEDULA)
    assert not cedula_proof.is_valid(token, "21", "87654321")
    assert not cedula_proof.is_valid(token, "21", "")
    exp, sig = token.split(".")
    assert not cedula_proof.is_valid(f"{int(exp) + 600}.{sig}", "21", CEDULA)
    assert not cedula_proof.is_valid(f"{exp}.{sig[:-1]}{'0' if sig[-1] != '0' else '1'}", "21", CEDULA)
    monkeypatch.setattr(cedula_proof.time, "time", lambda: int(exp) + 1)
    assert not cedula_proof.is_valid(token, "21", CEDULA)


def test_proof_lifetime_is_configurable(monkeypatch):
    monkeypatch.setattr(config, "CEDULA_PROOF_TTL_S", 30)
    monkeypatch.setattr(cedula_proof.time, "time", lambda: 1000)
    assert cedula_proof.issue("21", CEDULA).split(".")[0] == "1030"


# --- Por HTTP -----------------------------------------------------------------------

@pytest.mark.parametrize("token", [None, "", "inventado"])
def test_r30_unverified_id_number_is_ignored(client, token):
    """R30 · US2-AS12: cédula escrita a mano o inventada; no se guarda ni autoriza."""
    resp = identify(client, auth_id="21", cedula=CEDULA, cedula_token=token)
    assert_asks_for_card(resp)
    assert stored_cedula("21") == ""


def test_r30_by_name_without_proof(client):
    """R30 · US2-AS12: lo mismo cuando la autorización se resuelve por nombre."""
    assert_asks_for_card(identify(client, nombre="Pedro Sincedula", cedula=CEDULA))
    assert stored_cedula("21") == ""


def test_r31_proof_of_another_authorization(client):
    """R31 · EDGE-comprobante: comprobante emitido para otra autorización u otro número."""
    assert_asks_for_card(identify(client, auth_id="21", cedula=CEDULA, cedula_token=cedula_proof.issue("20", CEDULA)))
    assert_asks_for_card(identify(client, auth_id="21", cedula=CEDULA, cedula_token=cedula_proof.issue("21", "999")))
    assert stored_cedula("21") == ""


def test_r32_name_on_card_does_not_match(client, monkeypatch):
    """R32 · US2-AS13: el nombre leído no coincide; no hay comprobante."""
    read_card(monkeypatch, "REPUBLICA BOLIVARIANA\nJOSE OTRO APELLIDO\nV-12.345.678")
    resp = scan(client, "21")
    assert resp["match"] is False and resp["cedula_token"] is None
    assert_asks_for_card(identify(client, auth_id="21", cedula=resp["cedula"], cedula_token=resp["cedula_token"]))


def test_no_proof_without_authorization_or_number(client, monkeypatch):
    """Sin `auth_id`, o sin número leído, nunca se emite comprobante."""
    read_card(monkeypatch, "PEDRO SINCEDULA V-12.345.678")
    assert scan(client, "")["cedula_token"] is None
    assert scan(client, "999")["cedula_token"] is None
    read_card(monkeypatch, "PEDRO SINCEDULA", cedula=None)
    assert scan(client, "21")["cedula_token"] is None


def test_r33_matching_card_completes_the_authorization(client, monkeypatch):
    """R33 · US2-AS14 (control): nombre coincidente → comprobante → decide el estado real."""
    read_card(monkeypatch, "REPUBLICA BOLIVARIANA\nPEDRO SINCEDULA\nV-12.345.678")
    resp = scan(client, "21")
    assert resp["match"] is True and resp["cedula_token"]
    assert_authorized(identify(client, auth_id="21", cedula=resp["cedula"], cedula_token=resp["cedula_token"]))
    assert stored_cedula("21") == CEDULA


def test_r34_typed_id_number_is_accepted_in_access_request(client):
    """R34 · US2-AS15: en la solicitud de acceso decide el propietario; vale escrita."""
    resp = identify(client, request_mode=True, apartment="F-1", nombre="Juan Nuevo",
                    cedula=CEDULA, telefono="04141234567", motivo="")
    assert resp["action"] == "await_owner" and resp["request_id"]


def test_r35_proof_does_not_override_a_ban(client, monkeypatch):
    """R35 · US2-AS2: una autorización vetada completada con un comprobante válido sigue denegada."""
    read_card(monkeypatch, "SAUL VETADO V-12.345.678")
    resp = scan(client, "32")
    assert resp["match"] is True and resp["cedula_token"]
    final = identify(client, auth_id="32", cedula=resp["cedula"], cedula_token=resp["cedula_token"])
    assert_not_authorized(final)
    assert final["status"] == "DENIED" and not final["request_mode"]
