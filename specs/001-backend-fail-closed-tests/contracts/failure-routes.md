# Contrato: catálogo de rutas de fallo (SC-001)

Cada fila es una ruta de fallo que la suite MUST cubrir con al menos una prueba. «No autoriza»
significa: `status != "APPROVED"` **y** `action != "open_gate"`, con un `reply` no vacío cuando
la respuesta es una decisión de acceso (FR-003, FR-004).

## Canal de conversación — `POST /api/verify`

| ID | Fallo provocado | Resultado esperado | Escenario |
|---|---|---|---|
| R01 | El modelo de lenguaje no responde (error de conexión) | `ERROR` / `show_error` | US1-AS1 |
| R02 | El modelo devuelve JSON ilegible o sin `reply` | `ERROR` / `show_error` | US1-AS2 |
| R03 | Base de conocimiento ausente (sin contexto) y el modelo aprueba | Rebajada a `IDENTIFYING` | US2-AS9 (US1-AS3 lo cubre R04) |
| R04 | La consulta a la base de conocimiento lanza una excepción | No autoriza | US1-AS3 |
| R05 | `apartments.json` ausente o dañado | `ERROR` / `show_error` | US1-AS6 |
| R06 | El modelo responde `APPROVED` / `open_gate` | Rebajada a `IDENTIFYING` / `collect_info` | US2-AS9 |
| R07 | El modelo responde `open_gate` con un `status` distinto de `APPROVED` | Rebajada | US2-AS9 |
| R08 | El modelo responde `ring_bell` o un valor inexistente | Rebajada a `IDENTIFYING` / `collect_info` | US2-AS11 |
| R09 | El modelo responde `await_owner` o `show_id_scanner` | Rebajada | US2-AS9 |
| R10 | Mensaje del visitante con instrucciones para el modelo, y el modelo cede | Rebajada | US2-AS8, caso límite |

## Identificación por QR — `POST /api/verify-qr`

| ID | Fallo provocado | Resultado esperado | Escenario |
|---|---|---|---|
| R11 | QR vacío, ilegible o no base64 | `DENIED` (`invalid_format`) | caso límite |
| R12 | QR bien formado sin `id` o con `id` inexistente | `DENIED` (`not_found`) | US2-AS5 |
| R13 | `invitations.json` ausente | `DENIED` (`not_found`) | US1-AS6 |
| R14 | `invitations.json` dañado | `ERROR` / `show_error` | US1-AS6 |
| R15 | Excepción inesperada al evaluar | `ERROR` / `show_error` | US1-AS7 |
| R16 | QR con datos que contradicen el registro (vigencia, nombre, veto) | Decide el registro | US2-AS6 |

## Identificación por nombre — `POST /api/identify`

| ID | Fallo provocado | Resultado esperado | Escenario |
|---|---|---|---|
| R17 | `invitations.json` ausente | `NEED_INFO` en modo solicitud | US1-AS6 |
| R18 | `invitations.json` dañado | `ERROR` / `show_error` | US1-AS6 |
| R19 | Soft-IA falla al actualizar los datos de una autorización **vetada** | `DENIED` | US1-AS4 |
| R20 | Excepción inesperada al resolver el nombre | `ERROR` / `show_error` | US1-AS7 |
| R21 | `auth_id` inexistente | `DENIED` (`not_found`) | US2-AS5 |
| R36 | Homónimos, uno válido y uno vetado, identificados solo por nombre | `NEED_INFO` (pide inmueble); nunca `APPROVED` | caso límite |

## Solicitud de acceso — `/api/access-request`

| ID | Fallo provocado | Resultado esperado | Escenario |
|---|---|---|---|
| R22 | Soft-IA no responde al crear la solicitud | `DENIED` (`owner_unreachable`) — prueba existente | US1-AS4 |
| R23 | Soft-IA falla al consultar el estado (`GET`) | No autoriza | US1-AS4 |
| R24 | `request_id` inexistente | `DENIED` (`request_not_found`) | US1-AS7 |
| R25 | Excepción inesperada al cancelar (`DELETE`) | No autoriza | US1-AS7 |

## Voz y cédula

| ID | Fallo provocado | Resultado esperado | Escenario |
|---|---|---|---|
| R26 | Falla la transcripción (`POST /api/transcribe`) | `{"text": "", "error": "transcription_failed"}` | US1-AS5 |
| R27 | Falla la lectura de cédula (`POST /api/verify-cedula`) | `cedula: null`, `match: null`, `error` presente | US1-AS5 |

## Fallos combinados y posteriores a la decisión

| ID | Fallo provocado | Resultado esperado | Escenario |
|---|---|---|---|
| R28 | Modelo de lenguaje y Soft-IA caídos a la vez | Ninguna entrada autoriza a un visitante sin autorización vigente | caso límite |
| R29 | Falla el registro de la visita tras autorizar un QR válido | La respuesta al QR válido no cambia y un QR vetado sigue denegado | caso límite |

## Verificación de cédula (FR-015)

| ID | Situación provocada | Resultado esperado | Escenario |
|---|---|---|---|
| R30 | `cedula` enviada a `/api/identify` sin comprobante, para una autorización sin cédula | No se aplica; `NEED_INFO` / `show_id_scanner` | US2-AS12 |
| R31 | Comprobante alterado, caducado o emitido para otra autorización u otro número | No se aplica; `NEED_INFO` / `show_id_scanner` | caso límite |
| R32 | Cédula leída con nombre que no coincide | `match: false`, sin comprobante; la autorización no se completa | US2-AS13 |
| R33 | Cédula leída con nombre coincidente | Comprobante emitido; `/api/identify` decide por estado real | US2-AS14 (control) |
| R34 | Cédula escrita a mano en modo solicitud | Se acepta; la solicitud se crea | US2-AS15 |
| R35 | Autorización **vetada** completada con un comprobante válido | `DENIED`: el comprobante no altera el estado real | US2-AS2 |

## Cobertura existente que se referencia (no se duplica)

`test_access_requests.py`: `test_banned_visitor_never_gets_a_request` (US2-AS2 por nombre),
`test_expired_visitor_reuses_data` (US2-AS3), `test_do_not_disturb` (US2-AS7),
`test_softia_unreachable_denies` (R22), `test_reject`, `test_timeout`, `test_cancel`.
