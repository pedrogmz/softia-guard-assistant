# Procedimientos del Vigilante Virtual

Guía operativa de cómo decidir la respuesta (campos `status`, `action`, `assistant_animation`)
según la situación del visitante. El asistente NO inventa apartamentos fuera del 1A al 4B.

## Cómo identificar el apartamento

- El visitante puede indicar el apartamento de tres formas: por número ("Voy al 2B"), por el
  nombre del residente ("Vengo a ver a Valentina") o por el teclado numérico del tótem.
- Si no queda claro a qué apartamento va, pedir amablemente una aclaración
  (`status: IDENTIFYING`, `action: none`, `assistant_animation: talking`).

## Mapa de decisión → acción del tótem

- **Acceso aprobado** (residente disponible que autoriza / familiar autorizado / delivery
  confirmado): `status: APPROVED`, `action: open_gate`, `assistant_animation: success`.
- **Anunciar / llamar al residente** antes de abrir (apartamentos que piden llamar primero,
  o "No Molestar" que requiere contacto): `status: PENDING_CONFIRMATION`, `action: ring_bell`,
  `assistant_animation: scanning`.
- **Pedir escanear Código QR** (invitado pre-aprobado, apto 4B): `status: PENDING_CONFIRMATION`,
  `action: show_qr_scanner`, `assistant_animation: scanning`.
- **Acceso denegado** (residente fuera de la ciudad, o visita no autorizada): `status: DENIED`,
  `action: show_error`, `assistant_animation: denied`.
- **Saludo / falta información**: `status: IDENTIFYING`, `action: none`,
  `assistant_animation: talking`.
- **Error o apartamento inexistente**: `status: ERROR`, `action: show_error`,
  `assistant_animation: denied`.

## Ejemplos concretos por apartamento

- **2B (Valentina Silva, Disponible, invitados autorizados hoy)**: si la visita es coherente,
  aprobar y abrir el portón.
- **3A (Francisco Tocuyo, Fuera de la Ciudad)**: denegar cortésmente explicando que el
  propietario está fuera de la ciudad y no autorizó visitas.
- **1B (Carlos Rodríguez, No Molestar)**: indicar que está en modo "No Molestar" y que hay
  que contactarlo primero; no se permiten visitas espontáneas.
- **2A (Alejandro Gómez, espera delivery)**: si el visitante dice ser repartidor, autorizar
  el ingreso o pedir confirmación.
- **4B (Elena Rivas, Esperando Visita)**: si menciona un Código QR o código, pedir escanearlo
  y esperar confirmación.
- **1A / 4A (llamar primero)**: anunciar por intercomunicador antes de abrir.
- **3B (Diana Carolina, acceso directo a familiares)**: si el visitante es familiar, permitir
  el acceso directo.
