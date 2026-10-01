# Research: Suite de pruebas de fallo cerrado y decisión por estado real

**Fecha**: 2026-09-30 · **Spec**: [spec.md](spec.md) · **Plan**: [plan.md](plan.md)

No quedaron `NEEDS CLARIFICATION` en el contexto técnico. Esta fase recoge lo que se encontró al
leer el código y las decisiones de diseño que se derivan.

## 1. Estado de partida (verificado)

- Suite actual: `backend/tests/test_access_requests.py`, 12 pruebas, **pasan en 0,07 s** con
  `backend/.venv` (Python 3.14.7; la imagen Docker usa 3.12).
- `conftest.py` ya aísla los datos en un directorio temporal y simula Soft-IA
  (`SOFTIA_ENABLED=False`, `SOFTIA_SOLICITUD_MOCK=True`).
- Todos los puntos de entrada que deciden acceso envuelven su cuerpo en `try/except` y devuelven
  `ERROR_RESPONSE` (`status: ERROR`, `action: show_error`). La base de fallo cerrado existe; lo
  que falta es probarla y cerrar los huecos de abajo.

## 2. Defectos de fallo abierto encontrados (FR-010)

Leídos en el código durante la planificación. **Estado tras la implementación**: D3, D4, D5
y D9 se reprodujeron con pruebas que fallaban antes de la corrección; D1, D2 y D8 se
confirmaron retirando la corrección (la suite falla); D6 y D7 son de frontend y de prompt y se
verificaron en ejecución. Todos están corregidos. En las rutas de fallo de la historia 1 no
apareció ningún defecto.

| # | Dónde | Defecto | Requisito |
|---|---|---|---|
| D1 | `backend/app/main.py` `verify()` | Devuelve la respuesta del modelo tal cual: el modelo puede emitir `APPROVED` / `open_gate` sin ninguna autorización. | FR-013 |
| D2 | `backend/app/main.py` `verify()` + `frontend/src/App.tsx:380` | El modelo puede emitir `ring_bell`; el tótem simula el intercomunicador y a los 4 s da el acceso por autorizado. | FR-014 |
| D3 | `backend/app/invitations.py` `check_state()` | Una `autorizado_hasta` mal formada se ignora (`except ValueError: pass`) y la autorización se da por vigente. | FR-005, caso límite «campos desconocidos» |
| D4 | `backend/app/invitations.py` `check_state()` | Sin `autorizado_hasta`, la autorización no vence nunca. | caso límite «campos ausentes» |
| D5 | `backend/app/invitations.py` `check_state()` | `vetado` solo se reconoce como `1`, `"1"` o `True`; cualquier otro valor (`"true"`, `"si"`, `2`) se trata como no vetado. | caso límite «valores desconocidos» |
| D6 | `frontend/src/App.tsx:378` | El tótem abre con `action == "open_gate"` aunque `status` no sea `APPROVED`. | FR-003 (defensa en profundidad) |
| D8 | `backend/app/main.py` `identify()` | Acepta cualquier `cedula` que envíe el tótem para completar una autorización; la coincidencia de nombre (RF-17) solo la comprueba el tótem, y el número puede escribirse a mano. | FR-015 |
| D7 | `backend/app/prompt.py`, `backend/knowledge/*.md` | El prompt y las políticas indican al modelo aprobar y llamar por intercomunicador. | FR-013, FR-014 |
| D9 | `backend/app/access.py` `resolve_by_name()` | Con varios homónimos elige automáticamente el único válido, aunque otro esté vetado: un visitante vetado puede entrar con la autorización de un homónimo. | caso límite «homónimos» |

## 3. Decisiones

### 3.1 Guarda del canal de conversación (D1, D2)

- **Decisión**: una función pura de saneamiento aplicada a la salida del modelo en
  `/api/verify`, con **lista blanca**. Combinaciones permitidas: `IDENTIFYING` con `none` o
  `collect_info`; `PENDING_CONFIRMATION` con `show_qr_scanner`; `DENIED` o `ERROR` con
  `show_error`. Cualquier otra combinación se rebaja a `IDENTIFYING` / `collect_info` /
  `talking` con un mensaje fijo que pide identificarse (nombre o QR). Vive en un módulo propio
  (`backend/app/conversation.py`) para probarla sin HTTP.
- **Lectura tolerante**: la guarda recibe la respuesta del modelo leída de forma tolerante
  (`status` y `action` como texto libre). Todo valor fuera de la lista blanca, incluidos los que
  no existen en el esquema (`ring_bell`, valores inventados), se rebaja. `ERROR` queda solo para
  JSON ilegible o sin `reply`. Además, el esquema que se pasa a Ollama se restringe a los valores
  de la lista blanca.
- **Razón**: una lista blanca falla cerrado ante valores nuevos del enum; una lista negra
  (`APPROVED`, `ring_bell`) dejaría pasar el siguiente valor que se añada. El mensaje fijo evita
  repetir un «pase adelante» redactado por el modelo.
- **Alternativas descartadas**: (a) confiar solo en el prompt: el modelo puede ser convencido
  por el visitante; (b) restringir solo el JSON Schema que se pasa a Ollama: protege la
  generación, pero no un cambio futuro del esquema ni un doble de pruebas; se hace **además**.

### 3.2 Retiro de `ring_bell` (D2, FR-014)

- **Decisión**: eliminar `ring_bell` del enum `Action`, del prompt, de `knowledge/` y del
  frontend (rama `ring_bell`, estado `calling`, vista «Llamando»).
- **Razón**: RF-11 queda retirado; el contacto con el propietario es por WhatsApp (RF-20..23).
  Al salir del enum, el backend no puede emitirlo; si el modelo lo emite, la guarda lo rebaja
  (§3.1).
- **Alternativa descartada**: dejar el valor y solo filtrarlo; mantiene código muerto que
  autoriza sin respuesta real.

### 3.3 Estado real estricto (D3, D4, D5)

- **Decisión**: `check_state()` pasa a exigir prueba positiva de validez:
  - `vetado`: solo `0`, `"0"`, `False`, `None` o vacío significan «no vetado»; cualquier otro
    valor se trata como **vetado**.
  - `autorizado_hasta` ausente o mal formada → **`inactivo`** (no entra directo; puede pasar a la
    solicitud de acceso).
- **Razón**: principio IV («ante duda, no abrir»). El veto desconocido se resuelve por el lado
  más restrictivo; la fecha inválida se resuelve como `inactivo` para no dejar al visitante sin
  salida.
- **Evidencia**: en `backend/data/invitations.json` (24 registros sincronizados) `vetado` es
  siempre `0` o `1`, `estatus` es `activo` o `eliminado`, y ninguna `autorizado_hasta` está vacía
  ni mal formada. El cambio no altera ninguna decisión sobre los datos actuales.
- **Confirmado por el responsable del proyecto**: todas las autorizaciones llevan fecha; las
  permanentes usan una fecha de vencimiento muy lejana. No hay riesgo para ellas.

### 3.4 Dobles de prueba y ausencia de red (FR-009)

- **Decisión**: sustituir con `monkeypatch` los límites `llm.generate`, `rag.retrieve_context`,
  `stt.transcribe`, `ocr.extract_cedula` y las funciones de `softia`; añadir en `conftest.py` un
  fixture automático que bloquea las conexiones de red salientes.
- **Razón**: son los mismos límites que ya usa `test_softia_unreachable_denies`; no se añaden
  dependencias. El bloqueo de red convierte «sin red» en algo comprobado y no solo supuesto.
- **Alternativa descartada**: `pytest-socket` u otra librería; añade una dependencia para algo
  que resuelve un fixture de pocas líneas.

### 3.5 Trazabilidad prueba → escenario (FR-011)

- **Decisión**: cada prueba lleva en su docstring el identificador del escenario
  (`US1-AS3`, `US2-AS9`, `EDGE-veto-prevalece`, `R07`), y
  [contracts/failure-routes.md](contracts/failure-routes.md) lista las rutas `R01…` de SC-001.
- **Alternativa descartada**: marcadores de pytest personalizados; requieren registro y no
  aportan más que el docstring para una suite de este tamaño.

### 3.6 Frontend sin ejecutor de pruebas (D2, D6)

- **Decisión**: cambios mínimos en `App.tsx`, verificados con `npm run lint` y en el navegador.
  La regla de seguridad se prueba en el backend, que es quien deja de emitir las acciones.
- **Razón**: el principio VII lo prevé; adoptar un ejecutor de pruebas de frontend es otra
  feature.

### 3.7 Verificación de cédula exigida en el backend (D8, FR-015)

- **Decisión**: `/api/verify-cedula` devuelve, solo cuando hay `auth_id` y el nombre leído
  coincide, un **comprobante firmado** (`cedula_token`) que liga autorización, número de cédula
  y caducidad. `/api/identify` aplica una `cedula` a una autorización únicamente si llega con un
  comprobante válido para esa misma autorización y ese mismo número; si no, la ignora y vuelve a
  pedir la cédula a la cámara. La firma es un HMAC con un secreto aleatorio generado al arrancar
  el backend; caducidad de 10 minutos (configurable). Módulo propio:
  `backend/app/cedula_proof.py`.
- **Razón**: el backend comprueba por sí mismo que la verificación ocurrió sin guardar estado ni
  fiarse del tótem; es una función pura, fácil de probar y sin dependencias nuevas. Si el
  backend se reinicia, los comprobantes pendientes caducan y el visitante repite la lectura
  (falla cerrado).
- **Cédula escrita a mano**: no produce comprobante, así que no puede completar una
  autorización. En modo solicitud (`request_mode`) se sigue aceptando sin comprobante, porque
  decide el propietario. El tótem deja de ofrecer «escriba el número» fuera del modo solicitud
  y, tras 3 lecturas fallidas, deniega y remite al vigilante de turno.
- **Alternativas descartadas**: (a) guardar las verificaciones en memoria o en un archivo:
  añade estado y limpieza para lo mismo; (b) enviar la foto otra vez a `/api/identify`: duplica
  el OCR, la etapa más lenta y menos fiable.

### 3.8 Homónimos con una autorización vetada (D9)

- **Decisión**: `resolve_by_name()` solo prefiere la única candidata vigente cuando ninguna otra
  candidata está vetada ni es de otro condominio (es decir, las demás están vencidas o
  inactivas). Si alguna lo está, devuelve `ambiguous` y se pide desambiguar por cédula o
  inmueble; mientras no quede una sola candidata, no se autoriza.
- **Razón**: conserva el caso legítimo que ya cubre `test_expired_visitor_reuses_data` (la misma
  persona con una autorización vencida y otra de un día) y cierra el caso en que un visitante
  vetado entra con la autorización de un homónimo.
- **Límite conocido**: dos homónimos del mismo inmueble sin cédula que los distinga se quedan en
  `NEED_INFO`; no se abre, pero tampoco se les remite al vigilante.

## 4. Fuera de alcance (observado, no se corrige aquí)

- `SOFTIA_SOLICITUD_MOCK` vale `true` por defecto y habilita `/api/dev/access-request/{id}/respond`,
  que aprueba solicitudes sin propietario. **Se conserva a propósito** como vía de prueba cuando
  WhatsApp u otro servicio externo falle; queda como deuda técnica en `docs/requirements.md` §8.
- `/api/identify` acepta un `auth_id` aportado por el cliente. Pertenece al resto del punto 6 de
  la cobertura mínima (diálogo de datos faltantes).
- Al aprobar una solicitud, `_request_outcome()` no vuelve a evaluar el estado de la
  autorización recibida de Soft-IA. Pertenece a los contratos con Soft-IA (punto 4).
