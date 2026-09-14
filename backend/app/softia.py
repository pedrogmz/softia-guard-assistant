"""Cliente HTTP para la API de Soft-IA.

Autentica con un endpoint de login (usuario+contraseña -> token) y luego consulta
propietarios y autorizaciones del condominio con `Authorization: Bearer <token>`.
Todo es configurable por entorno (ver config.py). Este módulo solo obtiene datos;
el mapeo y la escritura local viven en `sync.py`.
"""
from __future__ import annotations

import logging
from typing import Any, Tuple

import httpx

from . import config

logger = logging.getLogger("guard-backend.softia")


class SoftIAError(Exception):
    pass


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=config.SOFTIA_BASE_URL,
        verify=config.SOFTIA_VERIFY_TLS,
        timeout=httpx.Timeout(20.0),
    )


async def _login(client: httpx.AsyncClient) -> str:
    if not (config.SOFTIA_USERNAME and config.SOFTIA_PASSWORD):
        raise SoftIAError("Faltan credenciales SOFTIA_USERNAME / SOFTIA_PASSWORD")
    payload = {
        config.SOFTIA_USERNAME_FIELD: config.SOFTIA_USERNAME,
        config.SOFTIA_PASSWORD_FIELD: config.SOFTIA_PASSWORD,
    }
    resp = await client.post(config.SOFTIA_LOGIN_PATH, json=payload)
    resp.raise_for_status()
    data = resp.json()
    token = data.get(config.SOFTIA_TOKEN_FIELD) if isinstance(data, dict) else None
    if not token:
        raise SoftIAError(f"El login no devolvió el campo '{config.SOFTIA_TOKEN_FIELD}'")
    return token


async def fetch_all(condominio_id: str) -> Tuple[Any, Any]:
    """Inicia sesión una vez y devuelve (propietarios, autorizaciones) crudos."""
    prop_path = config.SOFTIA_PROPIETARIOS_PATH.format(id=condominio_id)
    auth_path = config.SOFTIA_AUTORIZACIONES_PATH.format(id=condominio_id)
    async with _client() as client:
        token = await _login(client)
        headers = {"Authorization": f"Bearer {token}"}
        prop_resp = await client.get(prop_path, headers=headers)
        prop_resp.raise_for_status()
        auth_resp = await client.get(auth_path, headers=headers)
        auth_resp.raise_for_status()
        return prop_resp.json(), auth_resp.json()
