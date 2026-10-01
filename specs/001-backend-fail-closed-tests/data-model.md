# Data Model: Suite de pruebas de fallo cerrado y decisión por estado real

No se crean entidades ni almacenamiento nuevos. Este documento fija las reglas de decisión que
las pruebas comprueban sobre las entidades existentes.

## Autorización de visita (`invitations.json`)

| Campo | Uso en la decisión |
|---|---|
| `id` | Identidad; es lo único que se toma del QR. |
| `nombre`, `cedula`, `telefono` | Obligatorios; si falta alguno → `NEED_INFO` antes de decidir. |
| `idcondominios` | Si `CONDOMINIO_ID` está configurado y no coincide → `wrong_condominio`. |
| `vetado` | No vetado solo si es `0`, `"0"`, `False`, `None` o vacío; cualquier otro valor → `vetado`. |
| `estatus` | Válida solo si es `activo` (sin distinguir mayúsculas); cualquier otro → `inactivo`. |
| `autorizado_hasta` | Fecha ISO; vigente hasta ese día **inclusive**; ausente o mal formada → `inactivo`. |
| `inmueble`, `propietario`, `idpropietario` | Destino; no intervienen en la validez. |

### Orden de evaluación (`check_state`)

`wrong_condominio` → `vetado` → `inactivo` (estatus) → `inactivo` (fecha ausente/mal formada) →
`expired` → `ok`. El primer motivo que aplica gana; por eso el veto prevalece sobre una fecha
vigente.

### Estado → decisión

| Estado real | Por QR (`/api/verify-qr`) | Por nombre (`/api/identify`) | ¿Solicitud por WhatsApp? |
|---|---|---|---|
| `ok` + datos completos | `APPROVED` / `open_gate` | `APPROVED` / `open_gate` | — |
| `ok` + faltan datos | `NEED_INFO` | `NEED_INFO` | — |
| `vetado` | `DENIED` | `DENIED` | No |
| `wrong_condominio` | `DENIED` | `DENIED` | No |
| `expired` | `DENIED` | `NEED_INFO` (modo solicitud) | Sí |
| `inactivo` | `DENIED` | `NEED_INFO` (modo solicitud) | Sí |
| inexistente (`not_found`) | `DENIED` | `NEED_INFO` (modo solicitud) | Sí |
| QR ilegible (`invalid_format`) | `DENIED` | — | No |

## Resolución por nombre (`resolve_by_name`)

Tras desambiguar por cédula y por inmueble, si quedan varias candidatas con el mismo nombre:

- Si alguna está `vetado` o es `wrong_condominio` → `ambiguous`: se pide el inmueble y **no se
  autoriza** mientras no quede una sola.
- Si las demás están `expired` o `inactivo` y exactamente una es `ok` → se usa la vigente.

## Decisión de acceso (`VerifyResponse` / `GateResponse`)

- **Señales de autorización**: `status == "APPROVED"` y `action == "open_gate"`. Una respuesta
  es «no autorizada» solo si **ninguna** de las dos aparece (FR-003).
- **Acciones**: `open_gate`, `show_qr_scanner`, `collect_info`, `show_id_scanner`,
  `await_owner`, `none`, `show_error`. **`ring_bell` se elimina** (FR-014).
- **Quién puede emitir `APPROVED` / `open_gate`**: únicamente `/api/verify-qr`, `/api/identify`
  y `GET /api/access-request/{id}` con la solicitud aprobada. Nunca `/api/verify`.

## Comprobante de cédula (`cedula_token`)

| Atributo | Regla |
|---|---|
| Emisión | Solo `/api/verify-cedula`, con `auth_id` presente, número leído y nombre coincidente (`match == true`). |
| Contenido ligado | `auth_id`, número de cédula y caducidad (10 min por defecto). |
| Validación | `/api/identify` lo exige para aplicar `cedula` a una autorización; debe corresponder al mismo `auth_id` y al mismo número, y no estar caducado ni alterado. |
| Sin comprobante válido | La `cedula` se ignora: no se escribe en el libro mayor ni en Soft-IA, y la respuesta es `NEED_INFO` / `show_id_scanner`. |
| Modo solicitud | No se exige: la cédula escrita a mano se acepta. |

## Respuesta del canal de conversación (`/api/verify`)

La respuesta del modelo se lee de forma tolerante (`status` y `action` como texto) antes del
saneamiento; solo un JSON ilegible o sin `reply` produce `ERROR`. Combinaciones permitidas tras
el saneamiento (lista blanca):

| `status` | `action` permitidas |
|---|---|
| `IDENTIFYING` | `none`, `collect_info` |
| `PENDING_CONFIRMATION` | `show_qr_scanner` (solo si el visitante mencionó un QR o una invitación) |
| `DENIED` | `show_error` |
| `ERROR` | `show_error` |

Cualquier otra combinación que devuelva el modelo, incluidos valores que no existen en el
esquema (`ring_bell`), se **rebaja** a `IDENTIFYING` /
`collect_info` / `talking`, con un mensaje fijo que pide identificarse por nombre o QR. Se
conservan `apartment` y `owner`.

## Ruta de fallo

Par (punto de entrada, dependencia que falla). El catálogo completo, con el resultado esperado
de cada una, está en [contracts/failure-routes.md](contracts/failure-routes.md).

## Inmueble (`apartments.json`)

`status` que contiene «molestar» → «No Molestar»: no se crea solicitud y se responde `DENIED`
(`do_not_disturb`).
