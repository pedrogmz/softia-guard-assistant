"""Fixtures comunes: datos aislados en un directorio temporal y Soft-IA simulado."""
import json

import pytest
from fastapi.testclient import TestClient

from app import config, invitations, rag
from app.main import app

APARTMENTS = [
    {"apt": "F-1", "owner": "Paul Espinoza", "status": "Disponible", "notes": "", "idpropietario": "199630"},
    {"apt": "1B", "owner": "Laura Pérez", "status": "No Molestar", "notes": "", "idpropietario": "5"},
]

INVITATIONS = [
    {"id": "10", "nombre": "Ana Vetada", "cedula": "111", "idcondominios": "", "inmueble": "F-1",
     "propietario": "Paul Espinoza", "idpropietario": "199630", "autorizado_hasta": "2099-12-31",
     "estatus": "activo", "vetado": 1, "telefono": "0414"},
    {"id": "11", "nombre": "Carlos Vencido", "cedula": "222", "idcondominios": "", "inmueble": "F-1",
     "propietario": "Paul Espinoza", "idpropietario": "199630", "autorizado_hasta": "2020-01-01",
     "estatus": "activo", "vetado": 0, "telefono": "0412"},
]


@pytest.fixture
def client(tmp_path, monkeypatch):
    (tmp_path / "apartments.json").write_text(json.dumps(APARTMENTS), encoding="utf-8")
    (tmp_path / "invitations.json").write_text(json.dumps(INVITATIONS), encoding="utf-8")
    monkeypatch.setattr(config, "APARTMENTS_FILE", tmp_path / "apartments.json")
    monkeypatch.setattr(config, "INVITATIONS_FILE", tmp_path / "invitations.json")
    monkeypatch.setattr(config, "ACCESS_REQUESTS_FILE", tmp_path / "access_requests.json")
    monkeypatch.setattr(config, "PENDING_VISITAS_FILE", tmp_path / "pending_visitas.json")
    monkeypatch.setattr(config, "SOFTIA_ENABLED", False)
    monkeypatch.setattr(config, "SOFTIA_SOLICITUD_MOCK", True)
    monkeypatch.setattr(config, "CONDOMINIO_ID", None)
    rag.load_apartments.cache_clear()
    invitations.load_invitations.cache_clear()
    with TestClient(app) as c:
        yield c
    rag.load_apartments.cache_clear()
    invitations.load_invitations.cache_clear()
