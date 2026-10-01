"""Fixtures comunes: datos aislados en un directorio temporal, Soft-IA simulado y red
bloqueada. Todos los datos son ficticios."""
import json
import socket
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app import config, invitations, llm, rag
from app.main import app
from app.schemas import ModelReply

CONDO = "3304"

APARTMENTS = [
    {"apt": "F-1", "owner": "Paul Espinoza", "status": "Disponible", "notes": "", "idpropietario": "199630"},
    {"apt": "1B", "owner": "Laura Pérez", "status": "No Molestar", "notes": "", "idpropietario": "5"},
]


def _inv(id_, nombre, **over):
    record = {
        "id": id_, "nombre": nombre, "cedula": "900" + id_, "idcondominios": CONDO, "inmueble": "F-1",
        "propietario": "Paul Espinoza", "idpropietario": "199630", "autorizado_hasta": "2099-12-31",
        "estatus": "activo", "vetado": 0, "telefono": "0414000" + id_,
    }
    record.update(over)
    return record


def build_invitations() -> list:
    today = date.today()
    return [
        {"id": "10", "nombre": "Ana Vetada", "cedula": "111", "idcondominios": "", "inmueble": "F-1",
         "propietario": "Paul Espinoza", "idpropietario": "199630", "autorizado_hasta": "2099-12-31",
         "estatus": "activo", "vetado": 1, "telefono": "0414"},
        {"id": "11", "nombre": "Carlos Vencido", "cedula": "222", "idcondominios": "", "inmueble": "F-1",
         "propietario": "Paul Espinoza", "idpropietario": "199630", "autorizado_hasta": "2020-01-01",
         "estatus": "activo", "vetado": 0, "telefono": "0412"},
        _inv("20", "Marta Vigente"),
        _inv("21", "Pedro Sincedula", cedula=""),
        _inv("22", "Rosa Eliminada", estatus="eliminado"),
        _inv("23", "Oscar Otrocondo", idcondominios="9999"),
        _inv("24", "Hugo Hoy", autorizado_hasta=today.isoformat()),
        _inv("25", "Ines Ayer", autorizado_hasta=(today - timedelta(days=1)).isoformat()),
        _inv("26", "Lucas Sinfecha", autorizado_hasta=""),
        _inv("27", "Nora Malfecha", autorizado_hasta="31/12/2099"),
        _inv("28", "Tomas Vetotexto", vetado="true"),
        _inv("29", "Raul Gemelo", cedula="290290"),
        _inv("30", "Raul Gemelo", cedula="300300", inmueble="1B", propietario="Laura Pérez",
             idpropietario="5", vetado=1),
        _inv("31", "Vera Vetada", vetado=1, telefono=""),
        _inv("32", "Saul Vetado", vetado=1, cedula=""),
    ]


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """FR-009: ninguna prueba puede abrir una conexión de red saliente."""
    def blocked(self, *args, **kwargs):
        raise OSError("red bloqueada en las pruebas")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)


def reload_data():
    """Invalida las cachés tras modificar los archivos de datos en una prueba."""
    rag.load_apartments.cache_clear()
    invitations.load_invitations.cache_clear()


@pytest.fixture
def client(tmp_path, monkeypatch):
    (tmp_path / "apartments.json").write_text(json.dumps(APARTMENTS), encoding="utf-8")
    (tmp_path / "invitations.json").write_text(json.dumps(build_invitations()), encoding="utf-8")
    monkeypatch.setattr(config, "APARTMENTS_FILE", tmp_path / "apartments.json")
    monkeypatch.setattr(config, "INVITATIONS_FILE", tmp_path / "invitations.json")
    monkeypatch.setattr(config, "ACCESS_REQUESTS_FILE", tmp_path / "access_requests.json")
    monkeypatch.setattr(config, "PENDING_VISITAS_FILE", tmp_path / "pending_visitas.json")
    monkeypatch.setattr(config, "SOFTIA_ENABLED", False)
    monkeypatch.setattr(config, "SOFTIA_SOLICITUD_MOCK", True)
    monkeypatch.setattr(config, "CONDOMINIO_ID", None)
    # Sin índice vectorial ni Ollama: la recuperación semántica devuelve contexto vacío
    monkeypatch.setattr(rag, "retrieve_context", lambda *a, **k: [])
    reload_data()
    with TestClient(app) as c:
        yield c
    reload_data()


@pytest.fixture
def fake_llm(monkeypatch):
    """Sustituye el modelo de lenguaje: `fake_llm(status=..., action=...)` fija su respuesta
    cruda (texto libre en `status` y `action`); `fake_llm(raises=exc)` lo hace fallar."""
    def install(raises=None, **fields):
        def generate(_messages):
            if raises is not None:
                raise raises
            return ModelReply(**{"reply": "Respuesta del modelo.", **fields})

        monkeypatch.setattr(llm, "generate", generate)

    return install


@pytest.fixture
def fake_ollama(monkeypatch):
    """Sustituye el cliente de Ollama para devolver un contenido crudo (JSON o no)."""
    def install(content: str):
        class Client:
            def chat(self, **_kwargs):
                return {"message": {"content": content}}

        monkeypatch.setattr(llm, "_client", lambda: Client())

    return install
