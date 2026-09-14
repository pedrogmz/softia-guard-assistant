"""Sincronización del libro mayor local desde Soft-IA.

Alimenta `data/apartments.json` (propietarios/residentes) e `data/invitations.json`
(autorizaciones) desde los endpoints de Soft-IA cada cierto intervalo. Los datos
quedan en local para poder verificar visitas y autorizar accesos **aunque no haya
conexión** a Soft-IA. Si la consulta falla o viene vacía, se conservan los archivos
locales existentes (no se sobrescriben).

Uso manual:  python -m app.sync
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, List

from . import config, invitations, rag, softia

logger = logging.getLogger("guard-backend.sync")


def _as_list(payload: Any) -> List[dict]:
    """Extrae la lista de registros, tolerando envolturas como {'data': [...]}."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("data", "items", "results", "propietarios", "autorizaciones"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return []


def map_propietarios(items: List[dict]) -> List[dict]:
    """Soft-IA propietarios -> apartments.json ({apt, owner, status, notes}).
    La unidad es `codigo` y el dueño es `nombre` (con respaldos por robustez)."""
    out: List[dict] = []
    for it in items:
        apt = it.get("codigo") or it.get("inmueble") or it.get("apt")
        if not apt:
            continue
        owner = it.get("nombre") or it.get("propietario") or ""
        out.append({"apt": str(apt), "owner": owner, "status": "Disponible", "notes": ""})
    return out


def _index_propietarios(items: List[dict]) -> dict:
    """idpropietario -> registro de propietario, para cruzar con autorizaciones."""
    index: dict = {}
    for p in items:
        pid = p.get("idpropietario")
        if pid is not None:
            index[str(pid)] = p
    return index


def map_autorizaciones(items: List[dict], prop_by_id: dict) -> List[dict]:
    """Soft-IA autorizaciones -> invitations.json (libro mayor). Normaliza los
    nombres de campo al esquema que usa la validación del QR (id, estatus, vetado,
    autorizado_hasta, idcondominios) y **cruza con propietarios** para obtener la
    unidad (`inmueble`) y el nombre del dueño (`propietario`)."""
    out: List[dict] = []
    for it in items:
        pid = it.get("idpropietario")
        resident = prop_by_id.get(str(pid)) if pid is not None else None
        auth_id = it.get("idautorizacionvisitas", it.get("id"))
        out.append(
            {
                "id": str(auth_id) if auth_id is not None else "",
                "nombre": it.get("nombre"),
                "cedula": it.get("cedula"),
                "idcondominios": str(it.get("idcondominios", "")),
                "inmueble": (resident or {}).get("codigo") or it.get("inmueble"),
                "propietario": (resident or {}).get("nombre") or it.get("propietario"),
                "idpropietario": str(pid) if pid is not None else None,
                "autorizado_hasta": it.get("autorizado_hasta"),
                "estatus": it.get("estatus"),
                "vetado": it.get("flag_vetado", it.get("vetado", 0)),
            }
        )
    return out


def _atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)  # reemplazo atómico
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


async def sync_once() -> dict:
    """Ejecuta una sincronización. Devuelve un resumen; nunca lanza excepción."""
    if not config.CONDOMINIO_ID:
        return {"ok": False, "error": "CONDOMINIO_ID no configurado"}
    try:
        propietarios_raw, autorizaciones_raw = await softia.fetch_all(config.CONDOMINIO_ID)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Soft-IA no disponible (%s). Se conservan los datos locales.", exc)
        return {"ok": False, "error": str(exc)}

    propietarios_items = _as_list(propietarios_raw)
    autorizaciones_items = _as_list(autorizaciones_raw)
    apartments = map_propietarios(propietarios_items)
    invites = map_autorizaciones(autorizaciones_items, _index_propietarios(propietarios_items))
    result: dict = {"ok": True}

    # Solo se sobrescribe con datos no vacíos (evita borrar el libro mayor local)
    if apartments:
        _atomic_write_json(config.APARTMENTS_FILE, apartments)
        rag.load_apartments.cache_clear()
        result["apartments"] = len(apartments)
    else:
        result["apartments"] = "sin cambios (respuesta vacía)"

    if invites:
        _atomic_write_json(config.INVITATIONS_FILE, invites)
        invitations.load_invitations.cache_clear()
        result["invitations"] = len(invites)
    else:
        result["invitations"] = "sin cambios (respuesta vacía)"

    logger.info("Soft-IA sync: %s", result)
    return result


async def sync_loop() -> None:
    """Bucle en segundo plano: sincroniza al arrancar y luego cada intervalo."""
    while True:
        try:
            await sync_once()
        except Exception:  # noqa: BLE001
            logger.exception("Error inesperado en la sincronización")
        await asyncio.sleep(config.SOFTIA_SYNC_INTERVAL)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    print(asyncio.run(sync_once()))


if __name__ == "__main__":
    main()
