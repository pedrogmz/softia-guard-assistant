# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

La UI del tótem es una aplicación web (React + Vite) que corre a pantalla completa en el navegador del tótem físico. Web móvil y escritorio no son objetivos de producto.

## Users

**Visitante en la entrada del condominio (usuario principal).** Llega a pie o en vehículo al portón, a menudo con prisa, sin haber usado nunca el tótem. Necesita entrar, o saber con claridad por qué no, hablando o tocando la pantalla. Perfiles prioritarios confirmados:

- **Invitados con código QR** pre-aprobados por el residente vía Soft-IA: el camino más rápido.
- **Delivery y servicios** (repartidores, técnicos): prisa, a veces en moto o en vehículo; dicen o marcan el apartamento y necesitan resolver en segundos.
- **Visitas sin aviso**: el tótem les pide destino, nombre, cédula, teléfono y motivo. Luego esperan (cuenta regresiva, por defecto 120 s, cancelable) a que el propietario apruebe o rechace por WhatsApp vía Soft-IA.

**Actores secundarios** (no usan la UI del tótem):
- residente: aprueba o rechaza desde WhatsApp;
- vigilante humano: atiende excepciones y el botón de pánico;
- administración del condominio: gestiona datos y políticas en Soft-IA.

## Product Purpose

SoftiaGuard Assistant sustituye la verificación manual del vigilante en el portón por un **Vigilante Virtual**. Entiende al visitante por voz o texto en español, decide el acceso con IA local (LLM Ollama + RAG sobre las políticas del condominio) y responde por voz. Según la decisión, abre el portón, pide el QR o los datos, contacta al residente o deniega el acceso.

Éxito = accesos resueltos rápido, de forma consistente y auditable. Objetivos de validación propuestos, a medir en simulacros:
- respuesta extremo a extremo ≤ 5 s;
- identificación correcta ≥ 95 %;
- usabilidad ≥ 80/100.

Contexto: proyecto universitario con caso piloto en el Condominio Valle Blanco (Valencia, Venezuela). Ese nombre es un **placeholder**; la identidad del condominio es configurable por despliegue.

## Positioning

Un vigilante virtual **conversacional y local**, producto de la familia Soft-IA:
- toda la IA (STT Whisper, LLM, embeddings, RAG) corre en el servidor del condominio, sin nube;
- opera **offline-first** contra una copia local de los datos de Soft-IA;
- residentes, autorizaciones, QR de invitación, registro de visitas y solicitudes por WhatsApp se integran con Soft-IA.

## Operating Context

- **Tótem físico:** en **exterior**, a la intemperie. Debe leerse con sol directo y de noche. Pantalla táctil con micrófono, altavoz y cámara.
- **Orientación aún no definida:** la UI debe funcionar en vertical y en horizontal. El hardware definitivo está por proveer.
- **Flujos reales:**
  - voz: tocar para hablar → escucha → transcribe → verifica → respuesta hablada; también texto;
  - teclado de apartamento, con códigos reales de Soft-IA como «103», «PH2», «D-1» o «Casa 1-3»;
  - escaneo de QR por cámara;
  - lectura de cédula por cámara (OCR local), o tecleada;
  - datos faltantes paso a paso (`NEED_INFO`);
  - espera de la respuesta del propietario con cuenta regresiva y Cancelar.
- **Estados que la UI debe comunicar:** en espera, escuchando, entendiendo, verificando, respondiendo, autorizado, denegado, esperando al residente, sin conexión.
- **Idioma:** español, trato de «usted», respuestas concisas (máx. ~3 frases).

## Capabilities and Constraints

- La spec en `docs/` es la fuente de verdad, con badges ✅ implementado · 🟡 parcial/simulado · ⏳ pendiente.
- **No presentar como real lo simulado:** portón, intercomunicador, botón de pánico y canal WhatsApp (`SOFTIA_SOLICITUD_MOCK`) están simulados.
- **Fuera de alcance:** reconocimiento de placas (ANPR/LPR), reconocimiento facial y biometría, domótica más allá de portón e intercomunicador.
- **Privacidad:** el audio no sale del servidor local; el tótem nunca conoce el teléfono del propietario; cédula y teléfono no se muestran completos en pantalla.
- Cámara y micrófono requieren contexto seguro (localhost o HTTPS).
- **Stack existente:**
  - frontend: React 19, Vite 6, TypeScript, Tailwind CSS 4, motion y lucide-react;
  - backend: FastAPI, Ollama, ChromaDB y faster-whisper;
  - despliegue: Docker.
- **Multi-condominio:** nombre, ubicación, residentes y políticas del condominio se configuran por despliegue (RNF-10).
- **Lógica ya resuelta en el prototipo, a conservar:**
  - teclado alfanumérico de apartamento;
  - un dato por paso;
  - pánico con confirmación;
  - reinicio entre visitantes;
  - `?demo` para controles de simulación.

## Brand Commitments

- **SoftiaGuard es submarca de Soft-IA y es la marca visible del tótem.** Hereda el logo y los colores de Soft-IA.
- **Logo oficial de Soft-IA:** `~/Documents/soft-ia/softia/img/logo.png`. Es un edificio de trazos lineales con barras en celeste, azul marino y naranja, sobre un trazo tipo circuito, con «SOFT-IA» en naranja y letra técnica.
- **Colores observados en el logo** (aproximados a ojo; confirmar los valores exactos): azul marino ~#12263F, celeste ~#38BDF0, azul medio ~#1E88C8 y naranja ~#E8602F.
- **El condominio aparece como contexto:** su nombre es configurable y secundario frente a SoftiaGuard.
- Nombre del rol conversacional: **«Vigilante Virtual»**.
- **Voz:** cercana y cálida, sin perder el «usted». Amable incluso al denegar, breve y clara.

## Evidence on Hand

- Especificación: `docs/overview.md`, `docs/requirements.md`, `docs/architecture.md`.
- Logo de Soft-IA (ruta arriba). Hay otras variantes en `~/Documents/soft-ia/softia/img/` (`logo_mini.png`, `logo.ico`).
- Modelo 3D de guardia sin uso: `frontend/assets/Security_Guard.fbx`.
- Datos de ejemplo de residentes y autorizaciones en `backend/data/`, sincronizados desde Soft-IA local.
- **No existen todavía:** logo propio de SoftiaGuard, resultados de validación, fotos del tótem instalado ni testimonios. No fabricarlos.

## Product Principles

1. **Una respuesta clara en segundos.** Cada visita termina en un resultado inequívoco (entra, espera, muestra algo, o no entra y qué hacer), con los mínimos pasos.
2. **Nunca en silencio.** Cada fase tiene feedback visible y audible.
3. **Voz primero, toque siempre.** Todo lo que se puede decir se puede tocar; ningún camino depende de un solo canal.
4. **Tecnología cálida.** SoftiaGuard se siente actual y confiable, y el Vigilante habla con cercanía.
5. **Honestidad del estado.** Lo simulado se muestra como simulado; nunca se citan como palabras del visitante cosas que no dijo.

## Accessibility & Inclusion

- **Uso a la intemperie:** alto contraste legible con sol directo y de noche, tipografía grande legible a distancia de brazo.
- **Objetivos táctiles grandes**, usables con prisa, con guantes o desde un vehículo.
- **Doble canal (voz y toque) en cada paso**, para personas con dificultades auditivas o del habla y para entornos ruidosos.
