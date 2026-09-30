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
| RF-07 | Mostrar la **presencia del Vigilante** con estados visuales (espera/escucha/procesa/habla/autorizado/denegado) en la UI del tótem. | ✅ (personaje ilustrado con el trazo de Soft-IA; el avatar 3D FBX sigue sin uso) |
| RF-08 | Dar **feedback de procesamiento** al usuario (escuchando / entendiendo / verificando). | ✅ |
| RF-09 | Atender **invitados con código QR** pre-aprobados: escaneo real del QR con la cámara del tótem. | ✅ (escaneo real con jsQR; validación local) |
| RF-10 | **Abrir/cerrar el portón** (acceso peatonal y vehicular) según la decisión. | 🟡 (simulado en el frontend) |
| RF-11 | **Contactar al residente** por intercomunicador antes de autorizar. | 🟡 (simulado con temporizador) |
| RF-12 | **Botón de pánico** / alerta de emergencia, con confirmación y marcado como simulado mientras no haya integración. | 🟡 (simulado) |
| RF-13 | Consultar **residentes y autorizaciones** desde Soft-IA y mantenerlos en local (sincronización periódica, offline-first). | ✅ (operativa; el bucle automático requiere `SOFTIA_ENABLED=true`) |
| RF-14 | Registrar la **visita autorizada** (acceso por QR) en Soft-IA para auditoría, offline-first (encola y reintenta si no hay conexión). | ✅ (visitas por QR; requiere `SOFTIA_ENABLED=true`) |
| RF-15 | Verificar la **validez del QR de invitación** buscando su `id` en el libro mayor de autorizaciones y decidiendo con el **estado real** (`estatus`/`vetado`/vigencia; opcional `idcondominios`). | 🟡 (libro mayor local `invitations.json`; provisto por Soft-IA ⏳) |
| RF-16 | **Solicitar datos faltantes** {nombre, cédula, teléfono} antes de autorizar (diálogo dirigido por el backend, estado `NEED_INFO`), tanto en la identificación por QR como por voz/nombre. | ✅ |
| RF-17 | Leer la **cédula mostrada a la cámara** (OCR local Tesseract) y **verificar** que el nombre coincide con la autorización. | ✅ (fiabilidad de OCR limitada; best-effort con reintento) |
| RF-18 | **Actualizar la autorización** en Soft-IA (PATCH `cedula`/`telefono`) con los datos recogidos, y reflejarlo en el libro mayor local. | ✅ (requiere `SOFTIA_ENABLED=true`) |
| RF-19 | **Identificar por nombre** una autorización y **desambiguar** homónimos (por cédula, luego apartamento). | ✅ |
| RF-20 | **Solicitud de acceso** para visitantes **sin autorización vigente** (inexistente, vencida o inactiva): en lugar de denegar, recoger {inmueble destino, nombre, cédula, teléfono, motivo opcional} y generar una solicitud. Los **vetados** y de **otro condominio** se siguen denegando sin solicitud; los inmuebles con política "No Molestar" también. | ✅ (verificado contra Soft-IA real, condominio 3304) |
| RF-21 | **Notificar al propietario por WhatsApp vía Soft-IA** con los datos del visitante y botones **Aprobar / Rechazar**. El tótem nunca conoce el teléfono del propietario (Soft-IA lo resuelve por `idpropietario`). | 🟡 (envío del WhatsApp ✅ verificado; recepción de los botones por webhook en Soft-IA ⏳ por desplegar) |
| RF-22 | **Espera con tiempo límite**: el visitante ve una cuenta regresiva (por defecto 120 s, `ACCESS_REQUEST_TIMEOUT_S`) y puede **cancelar**; si el propietario rechaza o no responde, se deniega con un mensaje amable. | ✅ (vencimiento verificado contra Soft-IA real) |
| RF-23 | Al **aprobar**, se crea una **autorización de un día** (`autorizado_hasta` = fecha de hoy) en Soft-IA, se copia al libro mayor local, se registra la visita (RF-14) y se abre el portón. Si el visitante vuelve ese día, entra directo por nombre. | 🟡 (tótem ✅ verificado aprobando la solicitud directamente en la BD de Soft-IA; la creación desde el botón de WhatsApp depende del webhook ⏳) |

> Nota: el acceso **vehicular** se limita a RF-10 (control de portón). No se contempla
> reconocimiento automático de placas (ANPR/LPR) — ver alcance en [overview.md](overview.md#alcance).

## 3. Requerimientos no funcionales (RNF)

| ID | Requerimiento | Estado |
|---|---|---|
| RNF-01 | **Local / offline**: todo el procesamiento de IA corre localmente, sin servicios en la nube. **Excepción explícita**: la solicitud de acceso (RF-21) viaja por WhatsApp, un servicio externo, **a través de Soft-IA**; la decisión de IA sigue siendo local y, sin conexión, el tótem no puede contactar al residente (degrada a denegación). | ✅ |
| RNF-02 | **Privacidad**: el audio del visitante se procesa localmente y no se envía a terceros. | ✅ |
| RNF-03 | **Latencia y tiempos de respuesta** dentro de objetivos medibles (ver §7). | ⏳ (a validar) |
| RNF-04 | **Usabilidad**: interacción natural por voz con retroalimentación continua en cada fase. | ✅ / a validar |
| RNF-05 | **Degradación grácil / offline-first**: el backend responde aunque falte el índice RAG o falle una etapa; los datos de Soft-IA se guardan en local para verificar accesos **sin conexión**. | ✅ |
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

## 6. Integración con Soft-IA (REST)

El asistente se integra con Soft-IA mediante **API REST** con enfoque **offline-first**: sincroniza
los datos a archivos locales y opera contra ellos, para no depender de conexión constante.

| Operación | Descripción | Estado |
|---|---|---|
| **Sincronizar propietarios** | `GET /api/condominio/{id}/propietarios` → `apartments.json` (apt=`codigo`, owner=`nombre`). | ✅ |
| **Sincronizar autorizaciones** | `GET /api/condominio/{id}/autorizaciones` → `invitations.json` (id=`idautorizacionvisitas`, veto=`flag_vetado`, unidad/dueño por cruce con propietarios). | ✅ |
| **Autenticación** | Login (usuario+contraseña → token) y `Bearer` en cada consulta. | ✅ |
| **Registrar visita** | `POST /api/condominio/{id}/visitas` con `{idpropietario, idvisita, autorizado_por, fecha, telefono}` al autorizar un QR; encola y reintenta si falla por red. | ✅ |
| **Solicitud de acceso (WhatsApp)** | `POST /api/condominio/{id}/solicitud_acceso` con `{idpropietario, inmueble, nombre, cedula, telefono, motivo, expira_en}` → `{idsolicitud, estatus}` (`idpropietario` obligatorio; `motivo` opcional; `expira_en` en **segundos**). Si el WhatsApp no se puede enviar → **502** (Soft-IA la guarda como `error_envio`). `GET …/{sol}` → `{estatus: pendiente\|aprobada\|rechazada\|expirada\|cancelada, autorizacion?}` (404 si no existe; `error_envio` se informa como `cancelada`; una pendiente vencida, como `expirada`). `PATCH …/{sol}` `{estatus:"cancelada"}` (409 si ya no está pendiente). Soft-IA envía el WhatsApp y, al aprobar, **crea la autorización de un día**. **No se encola**: una solicitud que llega tarde no sirve. | 🟡 (crear/consultar/cancelar ✅ verificados; aprobación por webhook ⏳) |

Implementado y verificado con datos reales: cliente `app/softia.py` + sincronización periódica
`app/sync.py` (tarea en el ciclo de vida de FastAPI + `POST /api/sync` + CLI `python -m app.sync`) +
registro de visitas `app/events.py` (RF-14), con escritura atómica, conservación de los datos
locales si Soft-IA no responde, y **cola de reintento** para las visitas (offline-first). Detalle en
[architecture.md](architecture.md#6-integración-con-soft-ia-sincronización-offline-first).

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
| **Registro de accesos no-QR** | Se registran las visitas autorizadas por QR (con `idvisita`). Los accesos peatonales por LLM no tienen `idvisita`, así que aún no se auditan en Soft-IA (requeriría otro endpoint/estructura). |
| **Refresco del índice RAG tras sync** | `find_apartment` lee `apartments.json` fresco, pero los documentos de apartamentos en ChromaDB quedan del estado anterior hasta re-ejecutar `python -m app.ingest`. |
| **Webhook de WhatsApp en Soft-IA** | Los endpoints de `solicitud_acceso` (§6) y el envío de la plantilla ya funcionan. Falta **desplegar el webhook** que recibe los botones Aprobar/Rechazar: al aprobar debe crear la autorización de un día en `bas_autorizacionvisitas` y vincularla a la solicitud (`idautorizacionvisitas`). Mientras tanto, la aprobación se prueba actualizando la BD o, sin Soft-IA, con `SOFTIA_SOLICITUD_MOCK=true` + `POST /api/dev/access-request/{id}/respond`. |
| **Cancelar una solicitud ya vencida** | Al vencer, el tótem envía `PATCH … {estatus:"cancelada"}`; Soft-IA responde **409** porque ya la considera `expirada`. Es inocuo (el tótem solo registra un aviso), pero conviene que Soft-IA responda 200 en ese caso. |
| **Acciones físicas simuladas** | Portón, intercomunicador y pánico usan `setTimeout`; requieren integración con hardware/Soft-IA. |
