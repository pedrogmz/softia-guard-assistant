# CLAUDE.md — SoftiaGuard Assistant

Entrada del **desarrollo guiado por especificaciones (spec-driven)** de este proyecto. La
especificación vive en [`docs/`](docs/) y es la **fuente de verdad**: describe el *qué* y el *por
qué*. Los README describen el *cómo ejecutar*. Los principios no negociables del proyecto están en
la [constitución](.specify/memory/constitution.md), que prevalece sobre este archivo.

## Qué es el proyecto

**SoftiaGuard Assistant** es un asistente de vigilancia virtual de control de acceso para conjuntos residenciales. Atiende al visitante en un tótem de entrada por **voz o
texto**, decide el acceso con **IA local** (LLM Ollama + RAG) y responde por voz, ejecutando o
solicitando la acción del tótem (portón, solicitud al propietario por WhatsApp, QR o denegación). Todo el
procesamiento de IA es **local y open-source**, sin nube.

> **Objetivo general:** Diseñar un asistente de vigilancia virtual de control de acceso vehicular
> y peatonal conectado con el software **Soft-IA** usado en el condominio Valle Blanco ubicado en
> Valencia.

**Objetivos específicos:** (1) diagnosticar y establecer requerimientos; (2) diseñar arquitectura
y UI/UX; (3) desarrollar el prototipo e integrarlo con Soft-IA; (4) validar eficiencia (latencia,
tiempos de respuesta, usabilidad).

## Índice de la especificación

| Documento | Contenido |
|---|---|
| [`docs/overview.md`](docs/overview.md) | Contexto, objetivos, alcance, actores, estado actual vs objetivo, glosario. |
| [`docs/requirements.md`](docs/requirements.md) | Requerimientos funcionales, no funcionales, hardware, software, integración Soft-IA y criterios de validación. |
| [`docs/architecture.md`](docs/architecture.md) | Arquitectura tecnológica, flujos, contratos de API, RAG, integración Soft-IA y UI/UX. |
| [`.specify/memory/constitution.md`](.specify/memory/constitution.md) | Constitución: principios no negociables, restricciones, flujo de desarrollo y gobernanza. |
| `specs/NNN-feature/` | Spec, plan y tareas de **cada feature** (los crea Spec Kit; aún no hay ninguna). |

## Mapa objetivos → documentos

| Objetivo específico | Dónde se aborda |
|---|---|
| 1. Diagnóstico → requerimientos (técnicos/hardware/software) | [requirements.md](docs/requirements.md) |
| 2. Arquitectura tecnológica + UI/UX | [architecture.md](docs/architecture.md) |
| 3. Prototipo + integración con Soft-IA | Estado del prototipo marcado en toda la spec; integración en [architecture.md](docs/architecture.md#6-integración-con-soft-ia-sincronización-offline-first) |
| 4. Validación (latencia/tiempos/usabilidad) | [requirements.md](docs/requirements.md#7-criterios-de-validación-objetivo-4) |

## Convención de desarrollo guiado por especificaciones

Resumen operativo; las reglas completas están en la
[constitución](.specify/memory/constitution.md).

- La spec en `docs/` es la **fuente de verdad** del sistema completo. Todo cambio de
  comportamiento se **refleja primero en la spec** y luego en el código.
- Cada afirmación sobre funcionalidad lleva un **badge de estado**:
  - ✅ **Implementado** — existe y funciona en el prototipo.
  - 🟡 **Parcial / Simulado** — presente pero incompleto o simulado (p. ej. portón, QR).
  - ⏳ **Objetivo / Pendiente** — parte del objetivo, aún no construido (p. ej. Soft-IA).
- No presentar como hecho lo que es *mock*/simulado.

### Cuándo usar Spec Kit

| Tipo de cambio | Cómo se hace |
|---|---|
| **Funcionalidad nueva o cambio de comportamiento** | `/speckit-specify` → `/speckit-plan` → `/speckit-tasks` → `/speckit-implement`. Los artefactos quedan en `specs/NNN-feature/`. |
| **Corrección de documentación, bug menor, ajuste sin cambio de comportamiento** | Edición directa, sin Spec Kit. |
| **Cambio de principios o reglas del proyecto** | `/speckit-constitution`. |

`docs/` describe **cómo es el sistema hoy**; `specs/` guarda **cómo se decidió cada cambio**. Al
cerrar una feature, su resultado se vuelca en `docs/` (nuevo `RF`/`RNF`, badge, contrato) en el
mismo cambio.

## Estructura del repositorio

```
SoftiaGuardAssistant/
├── CLAUDE.md              # este índice (spec-driven)
├── docs/                  # especificación: overview · requirements · architecture
├── .specify/              # Spec Kit: constitución (memory/), plantillas y scripts
├── specs/                 # spec · plan · tareas por feature (se crea con la primera feature)
├── README.md             # cómo levantar el stack completo
├── frontend/             # UI del tótem (React + Vite + Three.js) — ver frontend/README.md
├── backend/              # API local (FastAPI + Ollama + RAG + Whisper) — ver backend/README.md
└── data/                 # vector store RAG persistido (ChromaDB)
```

Para build/run: [README raíz](README.md), [frontend/README.md](frontend/README.md),
[backend/README.md](backend/README.md).

## Nomenclatura y multi-condominio

- **Soft-IA** — software de gestión del condominio con el que se integra el asistente.
- **SoftiaGuard Assistant** — este proyecto (el asistente). Rol conversacional: "Vigilante Virtual".
- **Condominio Valle Blanco (Valencia)** — **placeholder** del proyecto universitario, **no** un
  destino fijo. La identidad del condominio (nombre, ubicación, residentes y políticas) es
  **configurable**: el producto está pensado para desplegarse en **distintos condominios**
  cambiando esa configuración.

> Hoy la identidad está **parcialmente hardcodeada**: el frontend usa `VITE_BUILDING_NAME`, pero el
> backend fija "Residencias El Ávila / Guatire" en el prompt, el `knowledge/` y los datos. Hacerla
> configurable end-to-end está registrado como deuda técnica en
> [requirements.md](docs/requirements.md#8-deuda-técnica--inconsistencias-a-corregir).
