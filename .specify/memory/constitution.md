# SoftiaGuard Assistant Constitution

## Core Principles

### I. Especificación primero (spec-driven)

- La especificación en `docs/` (overview, requirements, architecture) es la **fuente de verdad**
  del *qué* y el *por qué*; los README describen solo el *cómo ejecutar*.
- Todo cambio de comportamiento MUST reflejarse **primero** en la spec y **después** en el código.
- Todo requerimiento MUST tener un identificador trazable (`RF-nn`, `RNF-nn`) y todo cambio de
  código MUST poder vincularse a uno de ellos o a un ítem de deuda técnica (requirements §8).

**Razón:** es un proyecto académico con objetivos evaluables; sin trazabilidad spec → código no
se puede demostrar qué objetivo cumple cada parte del prototipo.

### II. IA local y privacidad (NO NEGOCIABLE)

- Todo el procesamiento de IA (LLM, embeddings, RAG, STT, OCR) MUST ejecutarse localmente con
  componentes open-source. Ningún servicio de IA en la nube.
- El audio, la imagen de cámara y los datos personales del visitante (nombre, cédula, teléfono)
  MUST NOT enviarse a terceros. El único destino externo permitido es **Soft-IA**.
- El tótem MUST NOT conocer ni almacenar el teléfono del propietario; Soft-IA lo resuelve.
- Cualquier excepción a la localidad MUST declararse explícitamente en la spec junto al
  requerimiento afectado (como la solicitud por WhatsApp vía Soft-IA en RNF-01).

**Razón:** el tótem capta voz, rostro y documentos de identidad en la entrada de un hogar; la
privacidad y la independencia de la nube son la premisa del producto, no una optimización.

### III. Honestidad de estado

- Cada afirmación de funcionalidad en la spec MUST llevar un badge: ✅ Implementado,
  🟡 Parcial / Simulado o ⏳ Objetivo / Pendiente.
- Lo simulado o *mock* MUST NOT presentarse como hecho, ni en la documentación ni en la interfaz
  (p. ej. el botón de pánico se marca como simulado mientras no haya integración).
- ✅ solo se asigna tras verificar el comportamiento en ejecución; si la verificación depende de
  una condición (flag, entorno, servicio externo), esa condición MUST constar junto al badge.
- Las inconsistencias conocidas MUST registrarse como deuda técnica en requirements §8.

**Razón:** en un sistema de seguridad, creer que algo funciona cuando está simulado es un riesgo
real; y en una tesis, es una afirmación falsa.

### IV. Offline-first y denegación segura

- El tótem MUST poder verificar accesos **sin conexión** contra los datos locales sincronizados
  desde Soft-IA; un fallo de sincronización MUST conservar los datos locales previos.
- Las escrituras hacia Soft-IA que siguen siendo útiles tarde (p. ej. registro de visitas) MUST
  encolarse y reintentarse; las que no (p. ej. solicitud de acceso) MUST NOT encolarse.
- El fallo de una etapa (RAG, STT, OCR, red) MUST degradar con un mensaje claro al visitante y
  nunca dejar el tótem sin respuesta.
- Ante duda, error o falta de datos, la decisión MUST ser **no abrir**: ninguna ruta de fallo
  puede terminar en acceso autorizado. Vetados y políticas restrictivas prevalecen siempre.

**Razón:** la entrada no puede depender de la red, y un control de acceso que falla abierto no es
un control de acceso.

### V. Soft-IA como fuente de verdad e identidad configurable

- Residentes, autorizaciones y vetos pertenecen a **Soft-IA**; los archivos locales son una copia
  de trabajo, nunca el origen. Los cambios de datos MUST propagarse a Soft-IA.
- La decisión de acceso MUST basarse en el **estado real** de la autorización (estatus, veto,
  vigencia), no en lo que el visitante declare ni en el contenido del QR por sí solo.
- La identidad del condominio (nombre, ubicación, residentes, políticas) MUST tratarse como
  **configuración**, no como código. "Valle Blanco / Valencia" es un placeholder; el código nuevo
  MUST NOT introducir más identidad hardcodeada.
- Toda verificación de la que dependa la decisión MUST exigirse en el **backend**; el tótem solo
  presenta y recoge datos, y nada de lo que envíe se da por verificado. En particular, para
  completar una autorización con la cédula del visitante, el backend MUST comprobar que el nombre
  leído en la cédula coincide con el de la autorización; una cédula escrita a mano MUST NOT
  completar una autorización (solo se admite en la solicitud de acceso, donde decide el
  propietario).
- Los contratos con Soft-IA MUST documentarse en la spec antes de consumirse.

**Razón:** el producto se despliega en distintos condominios y convive con un sistema de gestión
que ya es la autoridad sobre quién puede entrar.

### VI. Eficiencia medible y trato al visitante

- Latencia, tiempos de respuesta y usabilidad MUST validarse con mediciones contra los objetivos
  de requirements §7; no se declara "rápido" o "usable" sin datos de simulacros.
- Un cambio que afecte al camino crítico (STT → verificación → respuesta) MUST indicar su impacto
  esperado sobre esas métricas.
- El asistente MUST hablar en español formal (trato de "usted"), con respuestas concisas, y dar
  retroalimentación continua en cada fase (escuchando / entendiendo / verificando).
- Toda denegación MUST comunicarse con un mensaje amable y comprensible.

**Razón:** el objetivo 4 del proyecto es validar la eficiencia operativa; y quien usa el tótem es
una persona de pie en una entrada, sin manual ni paciencia para esperar.

### VII. Pruebas automatizadas

- Todo cambio de comportamiento MUST llegar con pruebas automatizadas que lo cubran, en el mismo
  cambio. Toda corrección de un defecto MUST incluir una prueba que falle sin la corrección.
- La suite MUST pasar completa antes de cada commit: `pytest` en `backend/` y `npm run lint`
  (comprobación de tipos) en `frontend/`. Una prueba que falla se arregla o se justifica; MUST NOT
  desactivarse ni borrarse para que la suite pase.
- Las pruebas MUST ser deterministas y ejecutarse **sin red**: Soft-IA, Ollama, Whisper y el OCR
  se sustituyen por dobles. MUST NOT usar datos personales reales.
- Las pruebas automatizadas no sustituyen la verificación en ejecución que exige el principio III
  para asignar ✅, ni las mediciones del principio VI.
- El frontend aún no tiene ejecutor de pruebas: mientras no se adopte uno, su comportamiento se
  verifica en el navegador y la lógica de decisión MUST residir en el backend, donde sí se prueba.

**Cobertura mínima obligatoria** (la suite MUST contener pruebas de cada punto):

1. **Fallo cerrado:** por cada ruta de fallo (Ollama caído, respuesta del LLM inválida, índice
   RAG ausente, Soft-IA inalcanzable, error de STT u OCR), el resultado nunca es acceso autorizado.
2. **Decisión por estado real:** autorización vetada, vencida, inactiva o de otro condominio →
   denegada; inmueble con política "No Molestar" → sin solicitud; QR con `id` inexistente → no abre.
3. **Offline-first:** una sincronización fallida conserva los archivos locales previos; el
   registro de visitas se encola y se reintenta; la solicitud de acceso no se encola.
4. **Contratos con Soft-IA:** el cliente maneja las respuestas documentadas en la spec (p. ej.
   502, 404 y 409 de `solicitud_acceso`) y envía los campos obligatorios.
5. **Solicitud de acceso:** aprobación, rechazo, vencimiento por tiempo límite y cancelación.
6. **Diálogo de datos faltantes:** estado `NEED_INFO`, verificación **en el backend** del nombre
   contra la cédula leída (y rechazo de la cédula sin verificar) y desambiguación de homónimos.
7. **Privacidad:** ninguna respuesta del backend al tótem contiene el teléfono del propietario.

**Razón:** los principios II, IV y V son promesas de seguridad; sin pruebas que las ejerzan en
cada cambio, son solo intenciones y una regresión que abra el portón pasaría inadvertida.

## Restricciones tecnológicas y de seguridad

- **Stack:** frontend React + Vite + TypeScript; backend FastAPI + Ollama + ChromaDB +
  faster-whisper. Las versiones vigentes son las de requirements §5. Añadir o sustituir un
  componente del stack MUST justificarse en la spec.
- **Despliegue:** contenedores Docker para frontend y backend; Ollama nativo en el host.
- **Secretos:** `.env` y credenciales MUST permanecer fuera del control de versiones; una
  credencial expuesta MUST rotarse.
- **Alcance:** reconocimiento de placas (ANPR/LPR), reconocimiento facial y biometría están
  **fuera de alcance**; incorporarlos exige enmendar primero `docs/overview.md`.
- **Acciones físicas:** portón, intercomunicador y pánico MUST permanecer marcados como simulados
  hasta que exista integración real con hardware.

## Flujo de desarrollo y puertas de calidad

1. **Especificar:** actualizar `docs/` (requerimiento, badge, contrato) antes de tocar código.
2. **Planificar:** todo plan MUST incluir una comprobación de esta constitución y justificar
   cualquier desviación.
3. **Implementar:** cambios acotados al requerimiento; sin funcionalidad no especificada.
4. **Probar y verificar:** añadir las pruebas automatizadas del cambio (principio VII) y pasar la
   suite completa; además, ejecutar el comportamiento real (no solo leer el código) antes de
   marcarlo ✅. Las integraciones con Soft-IA se verifican contra el servicio real o se marcan 🟡.
5. **Cerrar:** actualizar badges y deuda técnica en el mismo cambio. Los mensajes de commit MUST
   seguir Conventional Commits (`tipo(ámbito): descripción`) y escribirse en español, citando el
   `RF`/`RNF` cuando aplique.

## Governance

- Esta constitución prevalece sobre cualquier otra práctica del proyecto. Si entra en conflicto
  con la spec o el código, se corrige la spec o el código, o se enmienda la constitución.
- **Enmiendas:** se proponen por escrito con su justificación, las aprueba el responsable del
  proyecto y se registran actualizando este archivo junto con los documentos afectados.
- **Versionado (SemVer):** MAJOR — eliminación o redefinición incompatible de un principio;
  MINOR — principio o sección nuevos, o ampliación sustancial; PATCH — aclaraciones y redacción.
- **Cumplimiento:** toda revisión de plan, spec o cambio de código MUST comprobar estos
  principios. Una desviación solo se admite documentada, con su razón y la alternativa más
  simple descartada.
- `CLAUDE.md` es la guía operativa de desarrollo y MUST mantenerse coherente con este documento.

**Version**: 1.2.0 | **Ratified**: 2026-09-30 | **Last Amended**: 2026-09-30
