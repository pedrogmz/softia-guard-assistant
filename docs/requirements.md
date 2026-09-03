# Requerimientos — SoftiaGuard Assistant

> Cubre el **Objetivo específico 1** (diagnóstico → requerimientos técnicos, de hardware y
> software) y el **Objetivo específico 4** (criterios de validación). Parte de la especificación
> en [`../CLAUDE.md`](../CLAUDE.md).
> Convención de estado: ✅ Implementado · 🟡 Parcial / Simulado · ⏳ Objetivo / Pendiente.

## 1. Diagnóstico (situación actual)

El control de acceso del condominio depende de un vigilante humano que verifica manualmente al
visitante, contacta al residente y opera el portón. Limitaciones detectadas: dependencia del
criterio y disponibilidad del personal, tiempos de atención variables, ausencia de un registro
sistemático y auditable de accesos, y falta de una interfaz consistente para el visitante. De
este diagnóstico se derivan los requerimientos siguientes.

## 2. Requerimientos funcionales (RF)

| ID | Requerimiento | Estado |
|---|---|---|
| RF-01 | El visitante puede interactuar por **voz y por texto** en español. | ✅ |
| RF-02 | **STT local**: el audio del visitante se transcribe con Whisper en el backend, sin salir a la nube. | ✅ |
| RF-03 | **TTS**: el asistente responde con voz (síntesis en el navegador). | ✅ |
| RF-04 | Identificar el **apartamento/residente** por teclado numérico, número dicho o nombre del propietario. | ✅ |
| RF-05 | Decidir el acceso aplicando las **políticas del condominio** mediante LLM local + RAG. | ✅ |
| RF-06 | Devolver una **respuesta estructurada** (estado de acceso, acción del tótem y animación del avatar). | ✅ |
| RF-07 | Mostrar un **avatar 3D** del vigilante con estados visuales (espera/habla/escanea/éxito/denegado). | ✅ |
| RF-08 | Dar **feedback de procesamiento** al usuario (escuchando / entendiendo / verificando). | ✅ |
| RF-09 | Atender **invitados con código QR** pre-aprobados. | 🟡 (simulado; hardcodeado a la unidad 4B) |
| RF-10 | **Abrir/cerrar el portón** (acceso peatonal y vehicular) según la decisión. | 🟡 (simulado en el frontend) |
| RF-11 | **Contactar al residente** por intercomunicador antes de autorizar. | 🟡 (simulado con temporizador) |
| RF-12 | **Botón de pánico** / alerta de emergencia. | 🟡 (simulado) |
| RF-13 | Consultar **residentes y autorizaciones** desde Soft-IA. | ⏳ (hoy: mock local) |
| RF-14 | Registrar cada **evento de acceso** (entrada/decisión) en Soft-IA para auditoría. | ⏳ |
| RF-15 | Verificar la **validez de un código QR** de invitación contra Soft-IA. | ⏳ (hoy: simulado) |

> Nota: el acceso **vehicular** se limita a RF-10 (control de portón). No se contempla
> reconocimiento automático de placas (ANPR/LPR) — ver alcance en [overview.md](overview.md#alcance).

## 3. Requerimientos no funcionales (RNF)

| ID | Requerimiento | Estado |
|---|---|---|
| RNF-01 | **Local / offline**: todo el procesamiento de IA corre localmente, sin servicios en la nube. | ✅ |
| RNF-02 | **Privacidad**: el audio del visitante se procesa localmente y no se envía a terceros. | ✅ |
| RNF-03 | **Latencia y tiempos de respuesta** dentro de objetivos medibles (ver §7). | ⏳ (a validar) |
| RNF-04 | **Usabilidad**: interacción natural por voz con retroalimentación continua en cada fase. | ✅ / a validar |
| RNF-05 | **Degradación grácil**: el backend responde aunque falte el índice RAG o falle una etapa. | ✅ |
| RNF-06 | **Idioma**: español formal (trato de "usted"), respuestas concisas (máx. ~3 frases). | ✅ |
| RNF-07 | **Seguridad**: `.env` fuera del control de versiones; rotar la `GEMINI_API_KEY` heredada; autenticación/roles a futuro. | 🟡 |
| RNF-08 | **Portabilidad / despliegue**: contenedores Docker; Ollama nativo en el host para aprovechar GPU/Metal. | ✅ |
| RNF-09 | **Observabilidad**: logs de las etapas (verify/transcribe) para diagnóstico. | 🟡 (logging básico) |
| RNF-10 | **Configurable / multi-condominio**: la identidad del condominio (nombre, ubicación, residentes y políticas) es parametrizable para reutilizar el sistema en distintos condominios sin tocar código. "Valle Blanco / Valencia" es solo un placeholder. | 🟡 (frontend vía `VITE_BUILDING_NAME`; backend hardcodeado) |

## 4. Requerimientos de hardware

| Elemento | Descripción | Estado |
|---|---|---|
| **Tótem** | Terminal de entrada: pantalla táctil, micrófono, altavoz. | ⏳ (UI lista; hardware físico a proveer) |
| **Cámara** | Para escaneo de código QR de invitados (y verificación visual). | ⏳ |
| **Equipo de cómputo** | CPU + **GPU dedicada o Apple Silicon** con RAM suficiente para el LLM 7B (Ollama) y Whisper. | ✅ (entorno de desarrollo) |
| **Actuadores** | Portón vehicular/peatonal, intercomunicador, cerradura eléctrica. | 🟡 (interfaz simulada; falta puente a hardware) |
| **Red** | LAN estable del tótem al servidor local de Ollama y al servidor de **Soft-IA**. | ⏳ |

## 5. Requerimientos de software

**Frontend** — React `19` · Vite `6` · TypeScript `~5.8` · Three.js `0.185` · Tailwind CSS `4` ·
lucide-react `0.546` · motion `12` · Express `4` (proxy).

**Backend** — FastAPI `0.115.6` · uvicorn[standard] `0.34.0` · ollama `0.4.7` · chromadb `0.6.3` ·
pydantic `2.13.4` · python-dotenv `1.0.1` · python-multipart `0.0.20` · faster-whisper `1.1.1`.

**Modelos de IA (locales)** — LLM `qwen2.5:7b-instruct` (alt. `llama3.1:8b`) · embeddings `bge-m3` ·
STT Whisper `small` (device `cpu`, compute `int8`, idioma `es`).

**Runtime de IA** — Ollama (LLM + embeddings) · faster-whisper/CTranslate2 (STT) · ChromaDB
(vector store embebido).

> Detalle de versiones y configuración por defecto en [architecture.md](architecture.md) y en
> `backend/app/config.py`.

## 6. Integración con Soft-IA (REST) ⏳

El asistente debe integrarse con Soft-IA mediante **API REST**. Operaciones requeridas:

| Operación | Descripción |
|---|---|
| **Consultar residente** | Obtener datos y estado del residente por apartamento o por nombre. |
| **Verificar autorización** | Confirmar si un visitante/QR está autorizado para un apartamento. |
| **Registrar evento** | Persistir cada acceso/decisión (auditoría) en Soft-IA. |

Estado actual: **no existe integración**. Los datos de residentes son un *mock* local
(`backend/data/apartments.json`, 8 unidades) cargado en memoria. La arquitectura define una capa
de adaptador (`SoftIAClient`) para reemplazar el mock por el cliente REST sin cambiar el resto del
flujo — ver [architecture.md](architecture.md#6-capa-de-integración-soft-ia).

## 7. Criterios de validación (Objetivo 4)

Validación mediante **simulacros de acceso controlados**, midiendo:

| Métrica | Definición | Objetivo (propuesto) |
|---|---|---|
| **Latencia de STT** | Tiempo de transcripción del clip de voz (Whisper). | ≤ 2 s para clips ≤ 10 s |
| **Latencia de verificación** | Tiempo de la decisión de acceso (LLM + RAG) en `/api/verify`. | ≤ 3 s |
| **Tiempo de respuesta extremo a extremo** | Desde que el visitante termina de hablar hasta que el asistente responde por voz. | ≤ 5 s |
| **Tasa de identificación correcta** | % de solicitudes en que se identifica bien el apartamento/residente. | ≥ 95 % |
| **Usabilidad** | Facilidad de interacción percibida (p. ej. SUS o encuesta breve) en los simulacros. | ≥ 80/100 |

> Los valores objetivo son una propuesta inicial; se ajustan tras el diagnóstico de hardware
> definitivo. Método: batería de escenarios (acceso aprobado 2B, denegado 3A, QR 4B, delivery 2A,
> "No Molestar" 1B) repetidos por varios usuarios, con registro de tiempos por fase.

## 8. Deuda técnica / inconsistencias a corregir

| Ítem | Detalle |
|---|---|
| **Identidad del condominio como contenido placeholder** (RNF-10) | La identidad (nombre, ubicación, residentes, políticas) vive como **contenido de ejemplo** en el backend: el prompt (`prompt.py`), `knowledge/*.md` y `apartments.json` usan "Residencias El Ávila / Guatire"; el frontend usa `VITE_BUILDING_NAME` y "Guatire, VZLA" en el header. **Todo lo fijo se sustituye por el condominio real al momento de la implementación** (no es un defecto). Mejora propuesta para multi-condominio: hacerla **dirigida por configuración** en vez de editar código fuente. Nota menor: hoy los placeholders de frontend ("Valle Blanco") y backend ("El Ávila") difieren entre sí. |
| **`VITE_APP_NAME` sin uso** | Definida en `.env` pero no consumida en `App.tsx`. |
| **Restos del backend Gemini** | Referencias obsoletas en `frontend/metadata.json` y comentarios; rotar/eliminar `GEMINI_API_KEY` heredada. |
| **QR hardcodeado** | `handleSimulateQRScan` fija la unidad 4B/Elena Rivas; debe validarse contra Soft-IA. |
| **Acciones físicas simuladas** | Portón, intercomunicador y pánico usan `setTimeout`; requieren integración con hardware/Soft-IA. |
