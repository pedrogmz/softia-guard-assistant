"""Solicitud de acceso al propietario por WhatsApp (RF-20..23), en modo simulado."""
import time

from app import access_requests, config, invitations

VISITOR = {"nombre": "Juan Nuevo", "cedula": "12345678", "telefono": "04141234567"}


def identify(client, **fields):
    return client.post("/api/identify", json=fields).json()


def full_request(client, apartment="F-1", motivo="Entrega"):
    return identify(client, request_mode=True, apartment=apartment, motivo=motivo, **VISITOR)


def respond(client, request_id, decision):
    return client.post(f"/api/dev/access-request/{request_id}/respond", json={"decision": decision})


def test_unknown_visitor_enters_request_mode(client):
    resp = identify(client, nombre="Juan Nuevo")
    assert resp["status"] == "NEED_INFO"
    assert resp["request_mode"] is True
    assert resp["missing"][0] == "apartment"
    assert "WhatsApp" in resp["reply"]


def test_collects_fields_in_order(client):
    resp = identify(client, request_mode=True, nombre="Juan Nuevo", apartment="f 1")
    assert resp["missing"][0] == "cedula" and resp["action"] == "show_id_scanner"
    assert resp["apartment"] == "F-1"
    resp = identify(client, request_mode=True, nombre="Juan Nuevo", apartment="F-1", cedula="1")
    assert resp["missing"] == ["telefono", "motivo"]
    resp = identify(client, request_mode=True, apartment="F-1", **VISITOR)
    assert resp["missing"] == ["motivo"]


def test_unknown_apartment_is_asked_again(client):
    resp = identify(client, request_mode=True, apartment="Z-99", motivo="", **VISITOR)
    assert resp["status"] == "NEED_INFO" and resp["missing"] == ["apartment"]
    assert "Z-99" in resp["reply"]


def test_approve_opens_gate_and_saves_day_authorization(client):
    resp = full_request(client)
    assert resp["status"] == "PENDING_CONFIRMATION" and resp["action"] == "await_owner"
    rid = resp["request_id"]
    assert 0 < resp["expires_in"] <= config.ACCESS_REQUEST_TIMEOUT_S

    pending = client.get(f"/api/access-request/{rid}").json()
    assert pending["status"] == "PENDING_CONFIRMATION"

    assert respond(client, rid, "aprobada").status_code == 200
    resp = client.get(f"/api/access-request/{rid}").json()
    assert resp["status"] == "APPROVED" and resp["action"] == "open_gate"

    # Vuelve el mismo día: entra directo por nombre
    again = identify(client, nombre="Juan Nuevo")
    assert again["status"] == "APPROVED"
    record = invitations.find_authorization(f"mock-{rid}")
    assert record["inmueble"] == "F-1" and record["estatus"] == "activo"


def test_reject(client):
    rid = full_request(client)["request_id"]
    respond(client, rid, "rechazada")
    resp = client.get(f"/api/access-request/{rid}").json()
    assert resp["status"] == "DENIED" and "no autorizó" in resp["reply"]


def test_timeout(client, monkeypatch):
    rid = full_request(client)["request_id"]
    later = time.time() + config.ACCESS_REQUEST_TIMEOUT_S + 1
    monkeypatch.setattr(access_requests.time, "time", lambda: later)
    resp = client.get(f"/api/access-request/{rid}").json()
    assert resp["status"] == "DENIED" and "no respondió" in resp["reply"]
    # Ya vencida: el propietario no puede aprobarla tarde
    respond(client, rid, "aprobada")
    assert client.get(f"/api/access-request/{rid}").json()["status"] == "DENIED"


def test_cancel(client):
    rid = full_request(client)["request_id"]
    resp = client.delete(f"/api/access-request/{rid}").json()
    assert resp["status"] == "DENIED"
    assert access_requests.get(rid)["estatus"] == "cancelada"


def test_banned_visitor_never_gets_a_request(client):
    resp = identify(client, nombre="Ana Vetada")
    assert resp["status"] == "DENIED" and not resp["request_mode"]


def test_expired_visitor_reuses_data(client):
    resp = identify(client, nombre="Carlos Vencido")
    assert resp["status"] == "NEED_INFO" and resp["request_mode"]
    assert resp["missing"] == ["motivo"]  # inmueble, cédula y teléfono ya conocidos
    resp = identify(client, request_mode=True, auth_id=resp["auth_id"], motivo="")
    assert resp["action"] == "await_owner"
    respond(client, resp["request_id"], "aprobada")
    client.get(f"/api/access-request/{resp['request_id']}")
    # Tiene la vencida y la nueva de un día: entra con la vigente, sin preguntar el inmueble
    assert identify(client, nombre="Carlos Vencido")["status"] == "APPROVED"


def test_do_not_disturb(client):
    resp = full_request(client, apartment="1B")
    assert resp["status"] == "DENIED" and "no ser molestado" in resp["reply"]


def test_softia_unreachable_denies(client, monkeypatch):
    monkeypatch.setattr(config, "SOFTIA_SOLICITUD_MOCK", False)
    monkeypatch.setattr(config, "SOFTIA_ENABLED", True)
    monkeypatch.setattr(config, "CONDOMINIO_ID", "3304")

    async def boom(*_):
        raise ConnectionError("sin red")

    monkeypatch.setattr(access_requests.softia, "create_solicitud", boom)
    resp = full_request(client)
    assert resp["status"] == "DENIED" and "no puedo contactar" in resp["reply"]


def test_direct_api(client):
    resp = client.post("/api/access-request", json={"apartment": "F-1", **VISITOR}).json()
    assert resp["action"] == "await_owner"
