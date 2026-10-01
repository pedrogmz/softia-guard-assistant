# Implementation Plan: Suite de pruebas de fallo cerrado y decisión por estado real

**Branch**: `001-backend-fail-closed-tests` (directorio de la feature; la rama git actual es
`add_spec_kit`) | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-backend-fail-closed-tests/spec.md`

## Summary

Convertir en pruebas automatizadas dos promesas de la constitución: ningún fallo abre el portón
(principio IV) y el acceso se decide con el estado real de la autorización (principio V). La
suite cubre un catálogo de 35 rutas y los 22 escenarios de la spec, sin red.

Al leer el código aparecieron ocho defectos de fallo abierto ([research.md](research.md) §2).
Los principales: el canal de conversación devuelve tal cual lo que decide el modelo de lenguaje
(puede aprobar o «llamar al residente», que el tótem convierte en acceso a los 4 s);
`check_state()` da por vigente una autorización con fecha mal formada o un veto con valor
desconocido; y el backend acepta cualquier cédula que envíe el tótem para completar una
autorización. La feature los corrige con una guarda de lista blanca en `/api/verify`, el retiro
de `ring_bell` (RF-11), una evaluación de estado estricta y un comprobante firmado de la
verificación de cédula (RF-17 exigido en el backend).

## Technical Context

**Language/Version**: Python 3.12 en Docker (3.14.7 en `backend/.venv` local); TypeScript ~5.8
en el frontend

**Primary Dependencies**: FastAPI 0.115.6, pydantic 2.13.4, ollama 0.4.7, chromadb 0.6.3,
httpx 0.28.1; React 19 + Vite 6. No se añaden dependencias.

**Storage**: archivos JSON locales (`apartments.json`, `invitations.json`,
`access_requests.json`, `pending_visitas.json`); en pruebas, un directorio temporal por prueba

**Testing**: pytest 8.3.4 con `fastapi.testclient.TestClient` y `monkeypatch`; frontend solo
`npm run lint` (`tsc --noEmit`) y verificación en el navegador

**Target Platform**: backend local del tótem (Docker en Linux/macOS)

**Project Type**: aplicación web (backend FastAPI + frontend React)

**Performance Goals**: suite completa en menos de 30 s (hoy: 12 pruebas en 0,07 s)

**Constraints**: pruebas deterministas, sin red ni servicios externos, sin datos personales
reales; ninguna ruta de fallo puede terminar en acceso autorizado

**Scale/Scope**: 35 rutas, 22 escenarios de aceptación, unas 60–70 pruebas nuevas;
6 módulos de backend, 1 archivo de frontend, 2 documentos de `knowledge/` y la spec en `docs/`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Comprobación | Estado |
|---|---|---|
| I. Especificación primero | Los cambios de comportamiento (RF-05, retiro de RF-11, regla general de fallo cerrado, estado estricto) se escriben en `docs/` **antes** que el código; cada prueba se vincula a un escenario o ruta (FR-011). | ✅ Cumple (orden fijado abajo) |
| II. IA local y privacidad | No se añade ningún servicio externo. Las pruebas usan datos ficticios y bloquean la red. | ✅ Cumple |
| III. Honestidad de estado | Los defectos de research §2 se declaran «leídos, no reproducidos» hasta tener su prueba. Los badges de `docs/` se actualizan solo tras la verificación en ejecución (quickstart §6). | ✅ Cumple |
| IV. Offline-first y denegación segura | Es el objeto de la feature; la guarda usa lista blanca para fallar cerrado ante valores nuevos. | ✅ Cumple |
| V. Soft-IA como fuente de verdad | La decisión sale solo de las rutas que evalúan el registro; la coincidencia de nombre de la cédula pasa a exigirse en el backend (regla añadida en la constitución 1.2.0); no se añade identidad de condominio hardcodeada (los datos de prueba son ficticios). | ✅ Cumple |
| VI. Eficiencia medible y trato al visitante | Impacto en el camino crítico: la guarda es una comprobación en memoria (latencia despreciable), pero **una visita que antes se aprobaba conversando ahora necesita un paso más de identificación**, lo que alarga el tiempo extremo a extremo de esos casos. Los escenarios de simulacro de `docs/requirements.md` §7 ya se redefinieron. Quien no logre una lectura de cédula válida al completar una autorización ya no puede escribirla: se le deniega y se le remite al vigilante. El mensaje de rebaja es fijo, formal y amable. | ✅ Cumple, con impacto declarado |
| VII. Pruebas automatizadas | Toda corrección llega con una prueba que falla sin ella; suite sin red. El cambio de frontend se verifica en el navegador, como prevé el principio. | ✅ Cumple |

**Resultado**: sin violaciones. **Revisión tras el diseño (Fase 1)**: sin cambios; los
contratos y el modelo de datos no introducen nuevas desviaciones.

## Project Structure

### Documentation (this feature)

```text
specs/001-backend-fail-closed-tests/
├── plan.md              # Este archivo
├── research.md          # Fase 0: estado de partida, defectos encontrados, decisiones
├── data-model.md        # Fase 1: reglas de decisión sobre las entidades existentes
├── quickstart.md        # Fase 1: guía de validación
├── contracts/
│   ├── failure-routes.md        # Catálogo R01–R35 (SC-001)
│   └── conversation-channel.md  # Contratos de /api/verify, /api/verify-cedula y /api/identify
├── checklists/
│   └── requirements.md
└── tasks.md             # Fase 2 (/speckit-tasks; no lo crea /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── conversation.py      # NUEVO: guarda de lista blanca del canal de conversación
│   ├── cedula_proof.py      # NUEVO: comprobante firmado de la verificación de cédula
│   ├── main.py              # /api/verify aplica la guarda; identify exige el comprobante
│   ├── schemas.py           # Action pierde ring_bell; IdentifyRequest gana cedula_token
│   ├── config.py            # caducidad del comprobante
│   ├── invitations.py       # check_state() estricto (veto y fecha)
│   └── prompt.py            # el modelo ya no aprueba ni llama al residente
├── knowledge/
│   ├── politicas.md         # sin aprobación conversacional ni intercomunicador
│   └── procedimientos.md    # ídem (requiere re-ejecutar app.ingest)
└── tests/
    ├── conftest.py              # más datos ficticios, dobles, bloqueo de red
    ├── test_access_requests.py  # existente, sin cambios
    ├── test_fail_closed.py      # NUEVO: historia 1 (rutas de fallo)
    ├── test_state_decision.py   # NUEVO: historia 2 (estado real, QR y nombre)
    ├── test_conversation.py     # NUEVO: FR-013 / FR-014 (guarda y /api/verify)
    └── test_cedula_proof.py     # NUEVO: FR-015 (comprobante y /api/identify)

frontend/
└── src/
    └── App.tsx              # se elimina ring_bell / vista «calling»; abrir exige APPROVED;
                             # reenvía cedula_token; sin cédula escrita fuera de la solicitud

docs/
├── requirements.md          # RF-05, RF-11 retirado, RF-17, RNF-05, §4, §8 (§7 ya redefinido)
├── overview.md              # actores, alcance, estado
└── architecture.md          # contrato de /api/verify y enum action
```

**Structure Decision**: se mantiene la estructura web existente (`backend/` + `frontend/`). El
código nuevo son dos módulos pequeños, `backend/app/conversation.py` y
`backend/app/cedula_proof.py`; el resto son pruebas y cambios
acotados en archivos existentes. También se actualizan `README.md`, `frontend/README.md` y
`CLAUDE.md` donde mencionan el intercomunicador.

## Orden de trabajo

1. **Spec del sistema** (principio I): `docs/` recoge RF-05 nuevo, RF-11 retirado, fallo cerrado
   general, estado estricto y contrato de `/api/verify`, con badge ⏳.
2. **Infraestructura de pruebas**: `conftest.py` (datos ficticios por estado, dobles, bloqueo de
   red).
3. **Historia 1 (P1)**: pruebas de rutas de fallo; las que fallen confirman defectos.
4. **Historia 2 (P2)**: pruebas de estado real, del canal de conversación y de la verificación
   de cédula (fallan por D1–D5 y D8).
5. **Correcciones**: guarda, retiro de `ring_bell`, `check_state()` estricto, comprobante de
   cédula, prompt y `knowledge/`; después el frontend.
6. **Verificación y cierre**: quickstart completo; badges y deuda técnica en `docs/`.

## Complexity Tracking

Sin violaciones de la constitución que justificar.
