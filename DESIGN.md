---
name: SoftiaGuard Assistant
description: Videoportero Soft-IA. El tótem de acceso como un videointercomunicador de edificio bien hecho.
colors:
  navy: "#12263f"
  blue: "#1e88c8"
  sky: "#38bdf0"
  orange: "#e8602f"
  call: "#e8602f"
  call-lip: "#b3471f"
  orange-ink: "#12263f"
  frame: "#dfe5ec"
  frame-hi: "#eef2f6"
  frame-lo: "#c6cfd9"
  panel: "#eef2f6"
  screen: "#f7fafc"
  screen-edge: "#9fb0c3"
  ink: "#12263f"
  ink-soft: "#46586f"
  line: "#12263f"
  key: "#fbfcfd"
  key-edge: "#a9b8c8"
  key-ink: "#12263f"
  legend: "#1e88c8"
  grille: "#9fb0c3"
  bezel: "#1b2f48"
  focus: "#1e88c8"
  ok: "#157a4c"
  ok-tint: "#e3f4ea"
  no: "#b3261e"
  no-tint: "#fbe7e5"
  wait: "#1668a8"
  wait-tint: "#e2f0fa"
  frame-night: "#0d1b2d"
  frame-hi-night: "#16283f"
  frame-lo-night: "#08121f"
  panel-night: "#10223a"
  screen-night: "#0a1626"
  screen-edge-night: "#2a4462"
  ink-night: "#eef4fa"
  ink-soft-night: "#a9bdd2"
  line-night: "#38bdf0"
  key-night: "#162d4a"
  key-edge-night: "#2f5579"
  key-ink-night: "#8fd8f8"
  legend-night: "#38bdf0"
  bezel-night: "#050b14"
  ok-night: "#5fd39a"
  ok-tint-night: "#0f3326"
  no-night: "#ff8a80"
  no-tint-night: "#3a1618"
  wait-night: "#7cc8f5"
  wait-tint-night: "#0f2c46"
typography:
  display:
    fontFamily: "Rubik Variable, Rubik, system-ui, sans-serif"
    fontSize: "5.6rem"
    fontWeight: 700
    lineHeight: 1
    letterSpacing: "-0.03em"
    fontFeature: "tnum"
  headline:
    fontFamily: "Rubik Variable, Rubik, system-ui, sans-serif"
    fontSize: "2.6rem"
    fontWeight: 600
    lineHeight: 1.15
  state-title:
    fontFamily: "Rubik Variable, Rubik, system-ui, sans-serif"
    fontSize: "2.6rem"
    fontWeight: 700
    lineHeight: 1
    letterSpacing: "0.01em"
  title:
    fontFamily: "Rubik Variable, Rubik, system-ui, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 600
    lineHeight: 1.25
  body:
    fontFamily: "Rubik Variable, Rubik, system-ui, sans-serif"
    fontSize: "1.3rem"
    fontWeight: 400
    lineHeight: 1.375
  label:
    fontFamily: "Rubik Variable, Rubik, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 500
    lineHeight: 1.25
rounded:
  tag: "0.4rem"
  keypad: "0.7rem"
  key: "0.9rem"
  tile: "1rem"
  window: "1.2rem"
  screen: "1.6rem"
spacing:
  xs: "0.6rem"
  sm: "0.9rem"
  md: "1.2rem"
  lg: "1.4rem"
  xl: "1.6rem"
components:
  key-call:
    backgroundColor: "{colors.call}"
    textColor: "{colors.orange-ink}"
    rounded: "{rounded.key}"
    padding: "0.6rem 1.1rem"
    height: "4.2rem"
  key-call-talk:
    backgroundColor: "{colors.call}"
    textColor: "{colors.orange-ink}"
    rounded: "{rounded.key}"
    height: "6.2rem"
  key:
    backgroundColor: "{colors.key}"
    textColor: "{colors.key-ink}"
    rounded: "{rounded.key}"
    padding: "0.6rem 1.1rem"
    height: "4.2rem"
  key-quiet:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.key-ink}"
    rounded: "{rounded.key}"
    padding: "0.5rem"
    height: "3rem"
  key-alert:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.no}"
    rounded: "{rounded.key}"
    padding: "0.5rem"
    height: "3rem"
  keypad-key:
    backgroundColor: "{colors.key}"
    textColor: "{colors.key-ink}"
    rounded: "{rounded.keypad}"
    height: "3rem"
  state-tile-ok:
    backgroundColor: "{colors.ok-tint}"
    textColor: "{colors.ok}"
    rounded: "{rounded.tile}"
    padding: "1.2rem"
  state-tile-no:
    backgroundColor: "{colors.no-tint}"
    textColor: "{colors.no}"
    rounded: "{rounded.tile}"
    padding: "1.2rem"
  state-tile-wait:
    backgroundColor: "{colors.wait-tint}"
    textColor: "{colors.wait}"
    rounded: "{rounded.tile}"
    padding: "1.2rem"
  state-tile-off:
    backgroundColor: "{colors.key}"
    textColor: "{colors.ink}"
    rounded: "{rounded.tile}"
    padding: "1.2rem"
  sim-tag:
    rounded: "{rounded.tag}"
    padding: "0.1rem 0.5rem"
    typography: "{typography.label}"
  screen:
    backgroundColor: "{colors.screen}"
    textColor: "{colors.ink}"
    rounded: "{rounded.screen}"
  key-panel:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    rounded: "{rounded.screen}"
    padding: "1.2rem"
---

# Design System: SoftiaGuard Assistant

## Overview

**Creative North Star: "Videoportero Soft-IA"**

El tótem es el videoportero del edificio hecho bien. Tiene un marco de aluminio cepillado con letras grabadas y una lente de cámara asentada en el borde superior. A un lado está la pantalla de vidrio donde vive el Vigilante Virtual. Al otro, el panel de teclas físicas con rejilla de altavoz y una tecla de llamada naranja. Todo lo que aparece en pantalla debe poder existir en ese objeto. SoftiaGuard es una sub-marca de Soft-IA: el logo oficial va en una placa blanca, junto al wordmark tipográfico «SoftiaGuard». SoftiaGuard todavía no tiene logo propio.

La densidad es de quiosco público: pocas decisiones por pantalla, teclas grandes y una frase del Vigilante que se lee a distancia. El visitante siempre sabe en qué paso está, porque la franja superior de la pantalla lo nombra. La decisión llega por dos canales a la vez: la cara del Vigilante y la tecla-indicador del panel, que se enciende con corchetes de enfoque.

Hay dos iluminaciones. De día, el aluminio es claro y el grabado es azul marino. De noche, el panel es azul marino y las leyendas se retroiluminan en celeste. Mundos rechazados de forma explícita: el libro de registro con papel y sellos, el quiosco genérico de tarjetas redondeadas y el panel de control oscuro con neón.

**Alcance diseñado.** Esta ronda diseñó solo la pantalla de inicio y los estados de resultado: autorizado, no autorizado, en espera, sin conexión y cancelada. El teclado de apartamento, los pasos de datos, las páginas de cámara QR/cédula, la ayuda y la emergencia conservan su lógica y solo se re-estilizaron con tokens. Todavía les falta una ronda de diseño completa (ver Components › Pendiente). No son todavía una referencia del sistema.

**Key Characteristics:**
- Objeto físico: marco cepillado, vidrio con bisel, teclas con labio, rejilla de puntos, lente, grabado.
- Paleta de marca Soft-IA (azul marino, azul, celeste, naranja). El color fuera de la marca solo marca estado.
- Una sola tecla de llamada naranja por vista, con leyenda azul marino.
- Rubik autoalojada. La unidad base es 24px a tamaño de quiosco, y ningún texto baja de 1rem.
- El Vigilante está dibujado con el trazo lineal del logo de Soft-IA y cambia de expresión según el estado.
- Todo lo simulado lleva una marca visible.

## Colors

Hay una paleta de marca Soft-IA, dos juegos de neutros (día y noche) y un trío de estado. Nada más.

**Procedencia.** Los cuatro colores de marca (azul marino, azul, celeste y naranja) se tomaron a ojo del logo oficial (`frontend/public/brand/soft-ia-logo.png`). **Hay que confirmarlos** con el manual de marca de Soft-IA. Si cambian, se cambian en `:root` de `frontend/src/index.css` y en el frontmatter, y en ningún otro sitio.

### Primary
- **Azul Marino Soft-IA** (navy): el grabado del marco, la tinta de día, la leyenda de la tecla de llamada y la franja del nombre bajo la ventana del Vigilante (navy al 88%). Es la voz de la marca.
- **Naranja Llamada Soft-IA** (orange / call): el naranja exacto del logo. Se usa como relleno de la tecla de llamada, en la placa del uniforme y el distintivo de la gorra del Vigilante, y en una de las barras de acento. Su labio (call-lip) es un naranja tostado que hace de canto de la tecla.

### Secondary
- **Azul Soft-IA** (blue): las leyendas e iconos de las teclas en día, el anillo de foco, la selección y una barra de acento.
- **Celeste Retroiluminado** (sky): las leyendas nocturnas, las ondas de escucha, los nodos del circuito en espera y el punto «Vigilante Virtual».

### Neutral
- **Aluminio Claro** (frame, frame-hi, frame-lo): el marco de día. Las tres paradas forman el degradado del cepillado.
- **Vidrio de Día** (screen) y **Canto de Vidrio** (screen-edge): el fondo de la pantalla y su borde interior.
- **Tecla Blanca** (key), **Canto de Tecla** (key-edge) y **Tinta de Tecla** (key-ink): el cuerpo, el labio y el texto de las teclas.
- **Bisel** (bezel): el anillo oscuro alrededor del vidrio y de la lente.
- **Tinta Suave** (ink-soft): el texto secundario, las pistas y las etiquetas de la ficha. También es el color del grabado.
- **Noche** (sufijo `-night`): el marco y el panel pasan a azul marino profundo. Las teclas son azul pizarra con canto azul, y las leyendas y el trazo del Vigilante pasan a celeste.

### Estado
- **Verde Autorizado** (ok / ok-tint), **Rojo Denegado** (no / no-tint) y **Azul Espera** (wait / wait-tint). Cada uno tiene una variante nocturna más luminosa y un tinte oscuro.

### Named Rules
**La Regla del Color de Estado.** El verde, el rojo y el azul de espera solo aparecen cuando comunican un estado: el fondo de la ventana del Vigilante, la tecla-indicador, los corchetes, el punto de la franja, los nodos del circuito y la tecla de Emergencia. Nunca decoran. La marca Soft-IA pone el resto del color.

**La Regla de Sin Conexión.** Un fallo del sistema no es una negativa. «Sin conexión» usa neutros (key, ink, ink-soft), nunca el rojo de denegado.

**La Regla del Día y la Noche.** La iluminación se decide por la hora (`VITE_NIGHT_FROM` / `VITE_NIGHT_TO`, 18 → 6 por defecto) o se fuerza con `?tema=dia|noche`. Cada token de superficie tiene su pareja nocturna. No se escriben colores de superficie fuera de las variables.

## Typography

**Display Font:** Rubik Variable (autoalojada con `@fontsource-variable/rubik`; respaldo Rubik, system-ui, sans-serif)
**Body Font:** la misma
**Label/Mono Font:** la misma, con cifras tabulares (`tabular-nums`) para la hora, la cuenta regresiva y los datos

**Character:** una sola familia, técnica y redondeada, cálida sin ser infantil. Es la letra de las teclas del panel.

**Unidad base.** Todo se mide en rem. En horizontal, la raíz es `min(100vw / 80, 100dvh / 45)`, y en vertical es `min(100vw / 45, 100dvh / 80)`, con un piso de 12px. En ambos casos da **24px en 1920×1080 y en 1080×1920**. A tamaño de quiosco, 1rem = 24px.

### Hierarchy
- **Display** (700, 5.6rem, 1): la cuenta regresiva de la espera del residente. Siempre con cifras tabulares.
- **Headline** (600, 2.6rem; 2.35rem si la frase pasa de 80 caracteres; 1.15, `text-wrap: pretty`): la frase del Vigilante. Es el texto dominante de la pantalla.
- **State title** (700, 2.6rem, mayúsculas, 0.01em): el título de la tecla-indicador («AUTORIZADO», «SIN CONEXIÓN»).
- **Title** (600, 1.5rem): la etiqueta de las teclas principales del panel. La tecla Hablar sube a 2.2rem. El wordmark «SoftiaGuard» usa 700, 1.7rem, −0.01em.
- **Body** (400, 1.3rem, snug): la instrucción bajo la frase, el texto de la tecla-indicador (600) y los datos de la ficha (600, 1.5rem).
- **Label** (500–600, 1rem): las pistas de las teclas, la franja de paso (1.1rem), las etiquetas de la ficha, la marca de simulado y el grabado del marco (600, mayúsculas, 0.3em).

### Named Rules
**La Regla de los 24px.** Ningún texto baja de 1rem (24px a tamaño de quiosco). Si algo no cabe, se acorta el texto o se quita contenido. No se reduce el cuerpo.

## Layout

El marco ocupa la pantalla completa (`h-dvh`), con un margen interior de 1.4rem, 2.2rem arriba para la lente y 2.4rem abajo para el grabado. Dentro hay dos piezas: la pantalla de vidrio y el panel de teclas, separadas por 1.4rem.

- **Horizontal:** la pantalla y el panel quedan en fila, en proporción **1.38 : 1** (flex 1.38 / 1). Dentro de la pantalla, la ventana de video del Vigilante ocupa el 42% del ancho, a la izquierda, y la frase y la ficha llenan el resto.
- **Vertical:** la pantalla va arriba (flex 1.2) y el panel abajo (flex 1). Dentro de la pantalla, la ventana de video ocupa el **48% del alto** a todo el ancho, y la frase va debajo.
- **La franja de paso** recorre el borde superior de la pantalla. Tiene un punto de estado y el nombre del paso a la izquierda, y el condominio y la hora a la derecha.
- **El panel**, de arriba abajo: la placa de marca (logo + wordmark), la rejilla de altavoz (2.6rem de alto; 1.2rem cuando hay teclado), las teclas del paso alineadas al fondo y la fila del marco (Soy invitado · Ayuda · Emergencia) separada por un filete.
- **Ritmo:** los huecos del panel son de 0.9rem, los interiores de 1.2 a 1.6rem y las rejillas de teclas usan 0.6 a 0.7rem.

**La Regla de las Cuatro Teclas.** Un paso muestra como máximo cuatro teclas principales en el panel, sin contar la fila del marco. En el inicio son Hablar, Tengo código QR y Marcar apartamento.

## Elevation & Depth

La profundidad es física. No hay tarjetas flotantes: las sombras describen objetos (vidrio hundido en un bisel, teclas que se hunden, letras grabadas).

### Shadow Vocabulary
- **Vidrio** (`0 0 0 0.45rem var(--bezel), 0 0.5rem 1.4rem rgb(0 0 0 / 0.18), inset 0 0.4rem 1rem rgb(0 0 0 / 0.08)`): solo la pantalla.
- **Tecla** (`inset 0 0.12rem 0 rgb(255 255 255 / 0.35), 0 0.25rem 0 var(--key-edge), 0 0.5rem 1rem rgb(0 0 0 / 0.12)`): el canto duro inferior es el lateral de la tecla. Al pulsar baja 0.2rem y el canto se reduce a 0.05rem.
- **Tecla de llamada** (`inset 0 0.15rem 0 rgb(255 255 255 / 0.3), 0 0.3rem 0 var(--call-lip), 0 0.6rem 1.2rem rgb(0 0 0 / 0.16)`): al pulsar baja 0.25rem.
- **Panel** (`inset 0 0 0 0.12rem var(--key-edge), 0 0.4rem 1.2rem rgb(0 0 0 / 0.1)`): la placa de teclas encastrada en el marco.
- **Ventana de video** (`inset 0 0 0 0.12rem var(--screen-edge)`): un filete interior, sin sombra.
- **Grabado** (`text-shadow: 0 0.06rem 0 rgb(255 255 255 / 0.55), 0 -0.04rem 0 rgb(0 0 0 / 0.18)`; de noche `0.06` / `0.6`): letras hundidas en el aluminio.

### Named Rules
**La Regla del Canto de Tecla.** El desplazamiento duro (`0 0.25rem 0`) solo existe en las teclas, porque es su lateral físico. Nada que no se pueda pulsar lleva canto.

**La Regla Sin Neón.** No hay resplandores, glows ni sombras de color. De noche, la retroiluminación es un cambio de color de la leyenda (celeste), no un halo.

## Shapes

Las esquinas son suaves y escalonadas por tamaño de objeto: la pantalla y el panel usan 1.6rem, la ventana de video 1.2rem, la tecla-indicador 1rem, las teclas del panel 0.9rem, las teclas de teclado 0.7rem y la marca de simulado 0.4rem. Los bordes de las teclas miden 0.125rem en key-edge, y los de la tecla-indicador 0.22rem en el color del estado. Hay tres texturas propias:
- **Cepillado:** un degradado vertical frame-hi → frame-lo sobre vetas horizontales de 4px.
- **Rejilla de altavoz:** puntos de 0.13rem cada 0.7rem en color grille.
- **Rayado de simulado:** diagonales a −45° en `currentColor`.

La lente de cámara es un círculo de 1rem con anillo de bisel, centrado en el borde superior del marco.

## Components

### Buttons (teclas del panel)
- **Shape:** una tecla física con esquinas suaves (0.9rem), alto mínimo de 3rem y canto de tecla. El icono va a la izquierda (1.35em) y la etiqueta con su pista debajo. La variante *stacked* pone el icono encima y la etiqueta en 1rem, centrada.
- **Llamada (call):** relleno naranja Soft-IA con leyenda e icono **azul marino**. Solo hay una por vista: Hablar en el inicio (6.2rem de alto, 2.2rem de texto, ocupa el espacio libre) y Terminar / Empezar de nuevo en los resultados. Si falla la voz, el naranja pasa a «Tengo código QR».
- **Tecla (key):** cuerpo blanco (key) con canto key-edge. El icono va en la leyenda azul (celeste de noche).
- **Callada (quiet):** cuerpo del color del panel, para Volver, Cancelar y la fila del marco.
- **Alerta (alert):** cuerpo del panel con borde y texto rojo de denegado. Solo para Emergencia.
- **Pulsación:** la tecla baja 0.2–0.25rem en 90ms ease-out (transform y box-shadow). Deshabilitada: opacidad 45%.
- **Foco:** contorno de 0.25rem en focus con separación de 0.25rem.
- **Hablar escuchando:** la tecla pasa a cuerpo key con borde naranja de 0.2rem y texto naranja. Una barra naranja al 15% se llena de izquierda a derecha durante el límite de grabación, y los corchetes se cierran en naranja.

### Tecla-indicador de estado (StateTile)
La tecla del panel que «se enciende» con la decisión: borde de 0.22rem, fondo tinte y texto en el color del estado, icono de 3.2rem, título en mayúsculas y subtítulo. Entra con escala 0.96 → 1 en 300ms, y los corchetes de enfoque se cierran sobre ella.
- **Autorizado:** ok.
- **No autorizado:** no.
- **En espera / Llamando:** wait, con la cuenta regresiva en display.
- **Sin conexión:** neutro (key, ink, corchetes ink-soft).
- **Cancelada:** tono wait.

### Corchetes de enfoque (FocusBrackets)
Cuatro esquinas de 1.4rem con trazo de 0.22rem que sobresalen 0.55rem del objeto activo. Entran desde escala 1.12 con opacidad 0 y se cierran en 280ms (`cubic-bezier(0.16, 1, 0.3, 1)`). Se usan en la tecla-indicador, en Hablar mientras escucha y en el aviso de pánico.

### Marca de simulado (SimTag)
Una etiqueta con borde discontinuo de 0.1rem en `currentColor`, una muestra rayada de 1.2 × 0.8rem y un texto de 1rem en mayúsculas (0.04em). Hereda el color de su contexto. Obligatoria en todo lo que no está conectado a hardware real cuando `VITE_SIMULATION` es verdadero: portón, aviso al residente, llamada y alerta.

### Ficha de la visita (VisitCard)
Una rejilla de etiquetas autoajustable (mínimo 9rem por columna). Cada dato lleva su etiqueta en 1rem ink-soft, el valor en 600 a 1.5rem con cifras tabulares y un filete inferior de 0.15rem (key-edge; legend en el campo activo). En resultados solo se muestran los campos con datos. En pantalla pública, la cédula y el teléfono siempre van enmascarados.

### Franja de paso
Un punto de 0.75rem y el nombre del paso en 1.1rem semibold. El punto es azul de leyenda en reposo, naranja al escuchar, azul de espera al verificar o esperar, y verde o rojo con la decisión. Siempre nombra el paso actual.

### Placa de marca
El logo oficial de Soft-IA sobre una placa **blanca** de 3.6 × 3.4rem (también de noche, para respetar el logo), el wordmark «SoftiaGuard» y la línea «Vigilante Virtual · Unidad · por Soft-IA».

### El Vigilante Virtual (signature)
Un personaje en SVG con el trazo lineal del logo de Soft-IA: trazo constante de 9 (7 en detalles), puntas y uniones redondas, sin relleno salvo cara y gorra (color screen). Viste gorra con distintivo naranja, uniforme con cuello en V y una placa-escudo naranja. Lo acompañan las barras de acento del logo (celeste, naranja y azul) y un trazo de circuito con tres nodos. El trazo usa `--line`: azul marino de día y celeste de noche.
- **Estados de ánimo:** *idle* (sonrisa, parpadeo cada 5s), *listening* (cabeza −5°, ojos más gruesos, dos ondas celestes que laten), *thinking* (cabeza 4°, mirada lateral, nodos que se encienden en secuencia), *talking* (boca elíptica animada), *happy* (ojos en arco, sonrisa amplia, nodos verdes), *sad* (cejas caídas, boca plana, nodos rojos), *sorry* (cejas caídas, boca recta) y *waiting* (mirada lateral, nodos celestes fijos). La cabeza gira con un muelle (rigidez 120, amortiguación 14).
- **Encuadre horizontal (`slice`):** un primer plano que llena la ventana alta (viewBox 30 64 340 330). Las barras del logo se repiten en HTML en las esquinas superiores de la ventana (celeste + naranja a la izquierda, celeste + azul a la derecha, 0.45rem de grosor, al 9% del alto).
- **Encuadre vertical (`meet`):** la figura completa en la ventana ancha (viewBox 70 78 260 292), sin barras HTML.
- **Ventana de video:** el fondo es key en reposo y el tinte del estado con la decisión. Abajo lleva una franja «Vigilante Virtual» en navy al 88% con texto blanco.

### Motion
- **Cambio de visita:** la pantalla entra desde +24px y sale hacia −24px, en 400ms, `cubic-bezier(0.16, 1, 0.3, 1)`.
- **Tecla-indicador y corchetes:** 300 / 280ms con la misma curva.
- **Pulsación de tecla:** 90ms ease-out.
- **Valores nuevos de la ficha:** entran desde 6px en 300ms.
- **Con `prefers-reduced-motion`:** todas las animaciones y transiciones se anulan, el Vigilante no parpadea, las ondas y la boca quedan fijas y la barra de escucha no avanza.

### Pendiente (sin diseño propio todavía)
El teclado de apartamento (AptKeypad), los teclados numérico y alfabético, los pasos de datos (StepDisplay), las páginas de cámara QR y cédula, la ayuda y la emergencia solo están re-estilizados con tokens. Sus formas actuales no son reglas del sistema. Tienen pendiente una ronda de diseño completa.

## Do's and Don'ts

### Do:
- **Do** usar para la tecla de llamada el naranja Soft-IA exacto (#e8602f) con leyenda **azul marino** (#12263f). Nunca con texto blanco.
- **Do** mantener todo texto en 1rem o más (24px a tamaño de quiosco).
- **Do** marcar siempre lo simulado con la marca de simulado (portón, aviso, llamada, alerta) mientras `VITE_SIMULATION` esté activo.
- **Do** nombrar el paso actual en la franja de la pantalla y comunicar la decisión a la vez en la cara del Vigilante y en la tecla-indicador.
- **Do** limitar cada paso a cuatro teclas principales en el panel, como máximo.
- **Do** usar el color de estado solo para estado y tratar «sin conexión» con neutros.
- **Do** declarar cada color de superficie como variable con pareja nocturna.

### Don't:
- **Don't** volver al mundo del libro de registro: nada de papel, hojas, tapas, sellos ni tinta de sello. Es un mundo rechazado.
- **Don't** usar neón, glows, halos ni sombras de color, ni siquiera de noche.
- **Don't** citar como habla del visitante un resumen del sistema. En «Usted: «…»» solo va lo que el visitante dijo o escribió de verdad.
- **Don't** poner más de una tecla naranja en una misma vista.
- **Don't** animar transiciones de color (`transition-colors`, `transition-all`) sobre fondos que dependen del tema. El cambio día/noche debe ser instantáneo. En las teclas solo se animan transform y box-shadow.
- **Don't** usar el canto duro de tecla en nada que no se pueda pulsar.
- **Don't** usar el rojo de denegado para un fallo del sistema.
