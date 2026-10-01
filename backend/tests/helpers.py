"""Ayudantes compartidos por las pruebas de fallo cerrado y de decisión por estado."""
import base64
import json


def assert_not_authorized(resp: dict) -> None:
    """FR-003 / FR-004: ni el estado ni la acción autorizan, y hay mensaje para el visitante."""
    assert resp["status"] != "APPROVED", resp
    assert resp["action"] != "open_gate", resp
    assert resp["reply"].strip(), resp


def assert_authorized(resp: dict) -> None:
    assert resp["status"] == "APPROVED" and resp["action"] == "open_gate", resp


def make_qr(auth_id, **extra) -> str:
    """QR de invitación con el formato de Soft-IA: URL con el payload JSON en base64."""
    payload = base64.b64encode(json.dumps({"id": auth_id, **extra}).encode()).decode()
    return f"https://softia.example/app/control/detalles_visitante/abc?d={payload}"


def verify(client, message="Quiero visitar el F-1", **fields):
    return client.post("/api/verify", json={"message": message, **fields}).json()


def verify_qr(client, code):
    return client.post("/api/verify-qr", json={"code": code}).json()


def identify(client, **fields):
    return client.post("/api/identify", json=fields).json()
