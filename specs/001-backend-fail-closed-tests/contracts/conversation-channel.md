# Contrato: canal de conversación (`POST /api/verify`)

Cambio de contrato respecto a `docs/architecture.md`: el canal de conversación deja de poder
autorizar el acceso (FR-013) y de ordenar el intercomunicador (FR-014).

## Petición (sin cambios)

```json
{ "message": "Quiero visitar el 2B", "history": [], "currentAptInput": "" }
```

## Respuesta

```json
{
  "reply": "string (español formal, máx. ~3 frases)",
  "apartment": "string | null",
  "status": "IDENTIFYING | PENDING_CONFIRMATION | DENIED | ERROR",
  "owner": "string | null",
  "action": "none | collect_info | show_qr_scanner | show_error",
  "assistant_animation": "talking | scanning | idle | denied"
}
```

### Garantías

1. `status` nunca es `APPROVED` y `action` nunca es `open_gate`, sea cual sea la respuesta del
   modelo de lenguaje.
2. `action` nunca es `ring_bell` (el valor deja de existir), `await_owner` ni `show_id_scanner`;
   si el modelo emite cualquiera de ellos, la respuesta se rebaja.
3. Solo se devuelven las combinaciones de la lista blanca de
   [data-model.md](../data-model.md#respuesta-del-canal-de-conversación-apiverify).
4. Toda respuesta rebajada es `IDENTIFYING` / `collect_info` / `talking`, con un `reply` fijo que
   pide el nombre completo o el código QR, y conserva `apartment` y `owner`.
5. Ante cualquier excepción se devuelve la respuesta de contingencia: `ERROR` / `show_error`.

### Consecuencia para el tótem

Tras `collect_info`, el tótem continúa por `/api/identify`, que es quien decide con el estado
real de la autorización o deriva a la solicitud por WhatsApp. El tótem deja de tener la vista
«Llamando al residente».

## Verificación de cédula (FR-015)

`POST /api/verify-cedula` (formulario: `file`, `auth_id`) añade un campo a su respuesta:

```json
{ "cedula": "12345678", "match": true, "error": null, "cedula_token": "string | null" }
```

`cedula_token` solo es distinto de `null` cuando hay `auth_id`, se leyó un número y
`match == true`.

`POST /api/identify` admite un campo opcional nuevo, `cedula_token`. Reglas:

1. Fuera del modo solicitud, `cedula` solo se aplica a la autorización si `cedula_token` es
   válido para ese `auth_id` y ese número; si no, se ignora y la respuesta es `NEED_INFO` /
   `show_id_scanner`.
2. En modo solicitud (`request_mode: true`) `cedula` se acepta sin `cedula_token`.
3. Un comprobante válido no cambia la decisión por estado real: una autorización vetada,
   vencida o inactiva sigue sin autorizar.

## Otros contratos

`/api/verify-qr` y `/api/access-request` no cambian de forma. Cambia el enum compartido
`action`, que pierde `ring_bell`.
