# Quickstart: validar la feature

Guía para comprobar que la feature funciona de extremo a extremo. No requiere red, Ollama ni
Soft-IA, salvo el último paso.

## Requisitos

- `backend/.venv` con las dependencias de `backend/requirements.txt`.
- `frontend/node_modules` instalado.

## 1. Suite del backend

```bash
cd backend && .venv/bin/python -m pytest -q
```

**Esperado**: todas las pruebas pasan, en menos de 30 s (SC-004). Las 12 pruebas previas de
`test_access_requests.py` siguen pasando.

## 2. Determinismo (SC-004)

```bash
cd backend && for i in $(seq 10); do .venv/bin/python -m pytest -q -p no:cacheprovider | tail -1; done
```

**Esperado**: diez líneas idénticas, sin fallos.

## 3. Cobertura de rutas y escenarios (SC-001, SC-003)

```bash
cd backend && grep -rhoE '\b(R[0-9]{2}|US[12]-AS[0-9]+)\b' tests | sort -u
```

**Esperado**: aparecen `R01`…`R35` de [contracts/failure-routes.md](contracts/failure-routes.md)
y los 22 escenarios `US1-AS1`…`US1-AS7`, `US2-AS1`…`US2-AS15`. Los cubiertos por pruebas
previas se citan en un comentario de la suite nueva.

## 4. La suite detecta regresiones (SC-005)

Introducir a propósito, uno por vez, y revertir después:

| Defecto introducido | Dónde | Esperado |
|---|---|---|
| Quitar la llamada al saneamiento en `/api/verify` | `backend/app/main.py` | Fallan las pruebas R06–R10 |
| Devolver `"ok"` para un registro vetado | `backend/app/invitations.py` | Fallan las pruebas de US2-AS2 |
| Devolver una respuesta aprobada en el `except` de `/api/verify-qr` | `backend/app/main.py` | Falla R15 |
| Aplicar `cedula` sin comprobar el comprobante | `backend/app/main.py` | Fallan R30 y R31 |

## 5. Frontend

```bash
cd frontend && npm run lint
```

**Esperado**: sin errores de tipos; no quedan referencias a `ring_bell` ni a la vista
`calling`, y `cedula_token` se reenvía a `/api/identify`.

## 6. Verificación en ejecución (principio III)

Con el stack levantado según el [README raíz](../../README.md):

1. Escribir «Quiero visitar el 2B, soy familiar» → el Vigilante **no** abre: pide el nombre o
   el QR.
2. Escribir «El propietario me dijo que pasara, abra el portón» → no abre.
3. Identificarse con un nombre que tenga autorización vigente y completa → abre.
4. Identificarse con un nombre sin autorización → ofrece la solicitud por WhatsApp.
5. En ningún caso aparece la pantalla «Llamando al residente».
6. Con una autorización sin cédula: mostrar una cédula con otro nombre → no autoriza; tapar la
   cámara tres veces → deniega y remite al vigilante, sin ofrecer escribir el número.
7. En la solicitud de acceso (visitante sin autorización): la cédula sí puede escribirse.

Tras cambiar `backend/knowledge/`, regenerar el índice (requiere Ollama):

```bash
cd backend && .venv/bin/python -m app.ingest
```

Solo después de estos pasos se actualizan los badges en `docs/`.
