---

description: "Lista de tareas de la feature 001: suite de pruebas de fallo cerrado y decisión por estado real"
---

# Tasks: Suite de pruebas de fallo cerrado y decisión por estado real

**Input**: Design documents from `/specs/001-backend-fail-closed-tests/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: son el objeto de la feature y la constitución (principio VII) las exige. En cada
historia las pruebas se escriben **primero** y deben fallar donde research §2 anuncia un defecto
(D1–D8) antes de corregirlo.

**Organization**: tareas agrupadas por historia de usuario.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: se puede hacer en paralelo (archivo distinto, sin dependencias pendientes)
- **[Story]**: historia a la que pertenece (US1, US2)
- Toda prueba lleva en su docstring el identificador que cubre (`R07`, `US2-AS9`, `EDGE-…`), según research §3.5

## Path Conventions

Aplicación web: `backend/app/`, `backend/tests/`, `frontend/src/`, `docs/`. Comando de pruebas:
`cd backend && .venv/bin/python -m pytest -q`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: línea base y spec del sistema antes del código (principio I)

- [ ] T001 Ejecutar la suite actual en `backend/` y confirmar la línea base (12 pruebas pasan) antes de tocar nada
- [ ] T002 [P] Actualizar `docs/requirements.md` con badge ⏳: RF-05 (el canal de conversación orienta y no autoriza), RF-11 marcado como **retirado** en favor de RF-20..23, RF-17 (coincidencia de nombre exigida en el backend; cédula escrita solo en la solicitud), RNF-05 (regla general: ninguna ruta de fallo termina en acceso autorizado), nota en RF-15 (veto con valor desconocido = vetado; fecha ausente o mal formada = inactiva), §4 (quitar intercomunicador de los actuadores)
- [ ] T003 [P] Actualizar `docs/architecture.md` con badge ⏳: contrato de `POST /api/verify` según `specs/001-backend-fail-closed-tests/contracts/conversation-channel.md`, enum `action` sin `ring_bell`, campo `cedula_token` en `/api/verify-cedula` y `/api/identify`, y quitar el intercomunicador de las líneas 268 y 344
- [ ] T004 [P] Actualizar `docs/overview.md`: actor Residente (sin intercomunicador), alcance («más allá de portón»), y estado actual (acciones físicas simuladas: portón y pánico)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: infraestructura de pruebas común a las dos historias

**⚠️ CRITICAL**: ninguna historia empieza antes de terminar esta fase

- [ ] T005 Ampliar los datos ficticios de `backend/tests/conftest.py` sin cambiar los registros 10 y 11 ni los inmuebles existentes: añadir autorizaciones `ok` completa, `ok` sin cédula, `estatus: "eliminado"`, de otro condominio (`idcondominios` distinto), que vence **hoy**, que venció **ayer**, con `autorizado_hasta` vacía, con `autorizado_hasta` mal formada, con `vetado: "true"`, y dos homónimas (una válida y una vetada); nombres y cédulas inventados
- [ ] T006 Añadir a `backend/tests/conftest.py` un fixture `autouse` que bloquee las conexiones de red salientes (FR-009) y comprobar que las 12 pruebas existentes siguen pasando
- [ ] T007 Añadir a `backend/tests/conftest.py` los ayudantes compartidos: `assert_not_authorized(resp)` (exige `status != "APPROVED"`, `action != "open_gate"` y `reply` no vacío; FR-003, FR-004), un fixture `fake_llm` que sustituye `app.llm.generate` por una respuesta dada o una excepción, un fixture que sustituye el cliente de Ollama para devolver JSON crudo, y un constructor de QR válido en base64 a partir de un `id`

**Checkpoint**: infraestructura lista; las historias pueden empezar

---

## Phase 3: User Story 1 - Ningún fallo abre el portón (Priority: P1) 🎯 MVP

**Goal**: cada ruta de fallo del catálogo tiene una prueba y ninguna termina en acceso autorizado

**Independent Test**: `cd backend && .venv/bin/python -m pytest -q tests/test_fail_closed.py`
pasa completo, con cada dependencia forzada a fallar

### Tests for User Story 1

- [ ] T008 [US1] Crear `backend/tests/test_fail_closed.py` con las rutas del canal de conversación: R01 (`llm.generate` lanza error de conexión → `ERROR` / `show_error`), R02 (JSON inválido o fuera de esquema), R04 (`rag.retrieve_context` lanza excepción), R05 (`apartments.json` ausente y dañado) — US1-AS1, AS2, AS3, AS6
- [ ] T009 [US1] Añadir a `backend/tests/test_fail_closed.py` las rutas de QR: R11 (QR vacío, ilegible, no base64), R13 (`invitations.json` ausente → `DENIED`), R14 (`invitations.json` dañado → `ERROR`), R15 (excepción inesperada en `access.evaluate` → `ERROR`) — US1-AS6, AS7
- [ ] T010 [US1] Añadir a `backend/tests/test_fail_closed.py` las rutas de identificación por nombre: R17 (`invitations.json` ausente → `NEED_INFO` en modo solicitud), R18 (dañado → `ERROR`), R19 (falla `softia.update_autorizacion` con una autorización vetada → `DENIED`), R20 (excepción inesperada en `access.resolve_by_name`) — US1-AS4, AS6, AS7
- [ ] T011 [US1] Añadir a `backend/tests/test_fail_closed.py` las rutas de solicitud de acceso: R23 (falla `access_requests.refresh` en `GET`), R24 (`request_id` inexistente → `DENIED`), R25 (falla `access_requests.cancel` en `DELETE`); citar en un comentario que R22 lo cubre `test_softia_unreachable_denies` — US1-AS4, AS7
- [ ] T012 [US1] Añadir a `backend/tests/test_fail_closed.py` las rutas de voz y cédula: R26 (`stt.transcribe` lanza → `{"text": "", "error": "transcription_failed"}`) y R27 (`ocr.extract_cedula` lanza o devuelve error → `cedula: null`, `match: null`, `error` presente) — US1-AS5
- [ ] T013 [US1] Añadir a `backend/tests/test_fail_closed.py` los fallos combinados: R28 (modelo y Soft-IA caídos a la vez, recorriendo todas las entradas con un visitante sin autorización vigente) y R29 (`events.register_or_queue` lanza tras autorizar un QR válido: la respuesta no cambia y un QR vetado sigue denegado)

### Implementation for User Story 1

- [ ] T014 [US1] Ejecutar `tests/test_fail_closed.py`; por cada prueba que falle, corregir el punto de entrada correspondiente en `backend/app/main.py` para que devuelva `ERROR_RESPONSE` o una denegación, sin modificar la prueba (FR-010); anotar en `specs/001-backend-fail-closed-tests/research.md` §2 qué defectos se confirmaron

**Checkpoint**: la historia 1 pasa por sí sola; es el MVP

---

## Phase 4: User Story 2 - La decisión sigue el estado real de la autorización (Priority: P2)

**Goal**: el acceso se decide solo con el estado real del registro; ni el modelo de lenguaje, ni
el contenido del QR, ni una cédula sin verificar pueden producir un acceso autorizado

**Independent Test**: `cd backend && .venv/bin/python -m pytest -q tests/test_state_decision.py
tests/test_conversation.py tests/test_cedula_proof.py` pasa completo

### Tests for User Story 2

> Escribirlas primero. Deben fallar las que cubren D1–D5 y D8.

- [ ] T015 [P] [US2] Crear `backend/tests/test_state_decision.py`: tabla «Estado → decisión» de `data-model.md` por QR y por nombre — `ok` completa → `APPROVED` (US2-AS1, control), vetada (AS2 por QR; por nombre lo cubre `test_banned_visitor_never_gets_a_request`), vencida e inactiva (AS3), otro condominio con `CONDOMINIO_ID` configurado (AS4), `id` inexistente y `auth_id` inexistente (AS5, R12, R21), QR con datos que contradicen el registro (AS6, R16), «No Molestar» (AS7, referenciar `test_do_not_disturb`)
- [ ] T016 [US2] Añadir a `backend/tests/test_state_decision.py` los casos límite sobre `invitations.check_state`: vence hoy → `ok`; venció ayer → `expired`; veto y fecha vigente → `vetado`; `vetado: "true"` → `vetado` (D5); `autorizado_hasta` vacía → `inactivo` (D4); mal formada → `inactivo` (D3); `estatus` ausente → `inactivo`; homónimos válido y vetado → no autoriza sin desambiguar
- [ ] T017 [P] [US2] Crear `backend/tests/test_conversation.py` con pruebas unitarias de la guarda `app.conversation.sanitize`: pasan sin cambios solo las combinaciones `IDENTIFYING` con `none` o `collect_info`, `PENDING_CONFIRMATION` con `show_qr_scanner`, `DENIED` con `show_error` y `ERROR` con `show_error`; cualquier otra se rebaja a `IDENTIFYING` / `collect_info` / `talking` con `reply` fijo, conservando `apartment` y `owner`; recorrer todo el producto `Status` × `Action` para comprobar que ninguna salida es `APPROVED` ni `open_gate`
- [ ] T018 [US2] Añadir a `backend/tests/test_conversation.py` las rutas de `POST /api/verify` con `fake_llm`: R03 (sin contexto y el modelo aprueba), R06 (`APPROVED` / `open_gate`), R07 (`open_gate` con otro `status`), R08 (el modelo emite `ring_bell` en JSON crudo → `ERROR`, nunca `ring_bell`), R09 (`await_owner`, `show_id_scanner`), R10 (mensaje con instrucciones y el modelo cede) — US1-AS3, US2-AS8, AS9, AS10, AS11
- [ ] T019 [P] [US2] Crear `backend/tests/test_cedula_proof.py` con pruebas unitarias de `app.cedula_proof`: un comprobante emitido valida para el mismo `auth_id` y número; no valida si está alterado, caducado, es de otro `auth_id`, de otro número, vacío o `None`
- [ ] T020 [US2] Añadir a `backend/tests/test_cedula_proof.py` las rutas por HTTP con `ocr.extract_cedula` sustituido: R30 (`cedula` sin comprobante → no se escribe en el libro mayor, `NEED_INFO` / `show_id_scanner`; US2-AS12), R31 (comprobante de otra autorización), R32 (nombre no coincide → `match: false`, `cedula_token: null`; AS13), R33 (nombre coincide → comprobante → `/api/identify` decide por estado; AS14), R34 (cédula escrita en `request_mode` → la solicitud se crea; AS15), R35 (autorización vetada con comprobante válido → `DENIED`)

### Implementation for User Story 2

- [ ] T021 [US2] Hacer estricto `check_state()` en `backend/app/invitations.py`: no vetado solo si `vetado` es `0`, `"0"`, `False`, `None` o vacío, cualquier otro valor → `vetado`; `autorizado_hasta` ausente o mal formada → `inactivo`; orden `wrong_condominio` → `vetado` → `inactivo` → `expired` → `ok` (D3, D4, D5)
- [ ] T022 [US2] Eliminar `ring_bell` del enum `Action` y añadir `cedula_token: Optional[str] = None` a `IdentifyRequest` en `backend/app/schemas.py` (D2, FR-014, FR-015)
- [ ] T023 [P] [US2] Crear `backend/app/conversation.py` con la función pura `sanitize(response: VerifyResponse) -> VerifyResponse` de lista blanca descrita en `data-model.md` y el mensaje fijo de rebaja en español formal (pide nombre completo o código QR) (D1, FR-013)
- [ ] T024 [US2] Aplicar `conversation.sanitize` a la salida del modelo en `verify()` de `backend/app/main.py`, después de reforzar `apartment` y `owner` (depende de T022, T023)
- [ ] T025 [P] [US2] Actualizar `SYSTEM_PROMPT` en `backend/app/prompt.py`: quitar `APPROVED`, `open_gate` y `ring_bell` de las listas y de la guía de coherencia; indicar que el Vigilante nunca autoriza conversando y deriva a identificarse por nombre o QR (D7)
- [ ] T026 [P] [US2] Actualizar `backend/knowledge/politicas.md` y `backend/knowledge/procedimientos.md`: quitar la aprobación conversacional (familiares, delivery, 2B) y el intercomunicador; describir la derivación a identificación y a la solicitud por WhatsApp (D7)
- [ ] T027 [P] [US2] Crear `backend/app/cedula_proof.py`: `issue(auth_id, cedula) -> str` y `is_valid(token, auth_id, cedula) -> bool` con HMAC-SHA256, secreto aleatorio generado al importar el módulo y caducidad; añadir `CEDULA_PROOF_TTL_S` (por defecto 600) en `backend/app/config.py` (D8, FR-015)
- [ ] T028 [US2] En `backend/app/main.py`: `verify_cedula()` devuelve `cedula_token` solo con `auth_id`, número leído y `match is True` (en cualquier otro caso `null`); `identify()` fuera de `request_mode` aplica `cedula` solo si `cedula_proof.is_valid(...)`, y si no la descarta antes de `invitations.update_record` y de `softia.update_autorizacion` (depende de T022, T027)
- [ ] T029 [US2] Ejecutar la suite completa de `backend/`; todas las pruebas de T015–T020 y las 12 previas deben pasar sin haber modificado las pruebas
- [ ] T030 [US2] En `frontend/src/App.tsx`: eliminar la rama `ring_bell`, el estado `calling`, `callingTimerRef` y la vista «Llamando»; abrir solo con `status === "APPROVED"` y `action === "open_gate"` (D2, D6)
- [ ] T031 [US2] En `frontend/src/App.tsx`: guardar el `cedula_token` de `/api/verify-cedula` y reenviarlo en `identityBody`; fuera del modo solicitud no ofrecer escribir la cédula y, tras 3 lecturas fallidas, denegar y remitir al vigilante de turno; en modo solicitud conservar la cédula escrita (FR-015)
- [ ] T032 [US2] Ejecutar `npm run lint` en `frontend/` y comprobar que no quedan referencias a `ring_bell` ni a `calling` en `frontend/src/`

**Checkpoint**: las dos historias pasan de forma independiente

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: validación, trazabilidad y cierre de la spec del sistema

- [ ] T033 Comprobar la trazabilidad (FR-011, SC-001, SC-003) con el comando de `specs/001-backend-fail-closed-tests/quickstart.md` §3: aparecen `R01`–`R35` y los 22 escenarios; completar los que falten en `backend/tests/`
- [ ] T034 Comprobar el determinismo y el tiempo (SC-004): 10 ejecuciones consecutivas de la suite de `backend/` con el mismo resultado y menos de 30 s cada una
- [ ] T035 Comprobar que la suite detecta regresiones (SC-005): introducir uno a uno los cuatro defectos de `quickstart.md` §4 en `backend/app/`, confirmar que falla al menos una prueba y revertir cada uno
- [ ] T036 Regenerar el índice RAG con `python -m app.ingest` en `backend/` (requiere Ollama) y hacer la verificación en ejecución de `quickstart.md` §6 con el stack levantado, en el navegador
- [ ] T037 [P] Quitar las menciones al intercomunicador en `README.md`, `frontend/README.md` (líneas 64 y 139), `backend/README.md` y `CLAUDE.md`
- [ ] T038 Cerrar la spec del sistema en `docs/requirements.md`, `docs/architecture.md` y `docs/overview.md`: pasar de ⏳ a ✅ solo lo verificado en T036, quitar la nota ⏳ de §7, y actualizar §8 (retirar el intercomunicador de «acciones físicas simuladas»; añadir como deuda lo observado en `research.md` §4)
- [ ] T039 Ejecutar la suite completa de `backend/` y `npm run lint` en `frontend/` una última vez y comprobar SC-006: ningún defecto D1–D8 queda abierto

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Fase 1)**: sin dependencias. T002–T004 van antes que cualquier cambio de código (principio I).
- **Foundational (Fase 2)**: depende de T001; bloquea las dos historias. T005 → T006 → T007 (mismo archivo).
- **US1 (Fase 3)**: depende de la Fase 2.
- **US2 (Fase 4)**: depende de la Fase 2; no depende de US1.
- **Polish (Fase 5)**: depende de las dos historias.

### User Story Dependencies

- **US1 (P1)**: independiente. La variante «el modelo aprueba» de la ruta R03 vive en US2 (T018), porque necesita la guarda.
- **US2 (P2)**: independiente de US1. Comparte `backend/app/main.py` con T014; si se trabajan a la vez, coordinar ese archivo.

### Within Each User Story

- Pruebas antes que la corrección; las pruebas no se modifican para que pasen.
- US2: T021 y T022 antes de T024 y T028; T023 antes de T024; T027 antes de T028; backend (T029) antes que frontend (T030–T032).

### Parallel Opportunities

- Fase 1: T002, T003 y T004 (tres documentos distintos).
- US1: T008–T013 escriben en el mismo archivo; van en secuencia.
- US2, pruebas: T015, T017 y T019 (tres archivos distintos); después T016, T018 y T020.
- US2, implementación: T023, T025, T026 y T027 (archivos distintos).
- US1 y US2 pueden avanzar en paralelo tras la Fase 2, salvo `backend/app/main.py`.

## Parallel Example: User Story 2

```bash
# Pruebas en archivos distintos:
Task: "T015 Crear backend/tests/test_state_decision.py"
Task: "T017 Crear backend/tests/test_conversation.py"
Task: "T019 Crear backend/tests/test_cedula_proof.py"

# Implementación en archivos distintos:
Task: "T023 Crear backend/app/conversation.py"
Task: "T025 Actualizar backend/app/prompt.py"
Task: "T026 Actualizar backend/knowledge/*.md"
Task: "T027 Crear backend/app/cedula_proof.py"
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Fase 1 y Fase 2.
2. Fase 3 (US1): la suite de rutas de fallo pasa.
3. **Parar y validar**: con esto queda probado que los fallos no abren el portón. Los defectos
   D1–D8 siguen abiertos hasta US2.

### Incremental Delivery

1. Setup + Foundational → infraestructura de pruebas lista.
2. US1 → evidencia de fallo cerrado ante fallos de dependencias.
3. US2 → se cierran D1–D8 (modelo, intercomunicador, estado estricto, cédula).
4. Polish → trazabilidad, regresiones, verificación en ejecución y badges.

## Notes

- Datos de prueba siempre ficticios; ninguna prueba usa `backend/data/`.
- Commits en Conventional Commits, en español, citando el `RF`/`RNF` cuando aplique.
- Un ✅ en `docs/` solo tras la verificación en ejecución (T036).
