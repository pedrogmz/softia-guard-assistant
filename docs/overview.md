# Overview — SoftiaGuard Assistant

> Documento de visión general del proyecto. Parte de la especificación en [`../CLAUDE.md`](../CLAUDE.md).
> Convención de estado: ✅ Implementado · 🟡 Parcial / Simulado · ⏳ Objetivo / Pendiente.

## Contexto y problema

El **Condominio Valle Blanco** (Valencia, Venezuela) gestiona su operación con el software
**Soft-IA**. El control de acceso vehicular y peatonal en la entrada depende hoy de un vigilante
humano que verifica manualmente a los visitantes, contacta a los residentes y opera el portón.
Este proceso es lento, propenso a errores, difícil de auditar y depende de la disponibilidad y el
criterio del personal.

**SoftiaGuard Assistant** es un **asistente de vigilancia virtual** que atiende al visitante en un
tótem de entrada: entiende lo que desea (por voz o texto), verifica contra las políticas y los
datos del condominio, responde con voz, y ejecuta o solicita la acción correspondiente (abrir el
portón, consultar al propietario por WhatsApp, pedir un código QR o negar el acceso). Todo el procesamiento de IA
es **local y open-source**, sin dependencia de servicios en la nube.

> **Nota multi-condominio:** "Condominio Valle Blanco (Valencia)" es el **caso piloto /
> placeholder** del proyecto universitario, no un destino fijo. La solución se concibe como
> **reutilizable por distintos condominios**: la identidad (nombre, ubicación, residentes y
> políticas) es configurable y cambia en cada despliegue (ver
> [requirements.md](requirements.md#3-requerimientos-no-funcionales-rnf), RNF-10).

## Objetivo general

> Diseñar un asistente de vigilancia virtual de control de acceso vehicular y peatonal conectado
> con el software Soft-IA usado en el condominio Valle Blanco ubicado en Valencia.

## Objetivos específicos

1. **Diagnosticar** los procesos actuales de control de acceso y las condiciones físicas del
   condominio para establecer los requerimientos técnicos, de hardware y de software del
   asistente. → ver [requirements.md](requirements.md)
2. **Diseñar** la arquitectura tecnológica y la interfaz gráfica (UI/UX) del asistente con las
   herramientas seleccionadas. → ver [architecture.md](architecture.md)
3. **Desarrollar** el prototipo del asistente integrando la arquitectura y vinculándolo con la
   plataforma Soft-IA. → estado del prototipo marcado en toda la spec; integración en
   [architecture.md](architecture.md).
4. **Validar** la eficiencia operativa mediante simulacros de acceso controlados para medir la
   latencia, los tiempos de respuesta y la usabilidad de la interacción. → criterios en
   [requirements.md](requirements.md#7-criterios-de-validación-objetivo-4).

## Alcance

**Dentro del alcance:**
- Atención al visitante por **voz y texto** en español.
- Identificación del apartamento/residente y **decisión de acceso** según las políticas del
  condominio (asistida por IA local + RAG).
- Control de acceso **peatonal** (visitantes) y **vehicular limitado a la apertura/cierre del
  portón** por decisión del asistente/vigilante.
- Integración con **Soft-IA** vía API REST (consulta de residentes/autorizaciones y registro de
  eventos de acceso).
- Interfaz del tótem con el **Vigilante como personaje**, retroalimentación por voz y estados visuales.

**Fuera del alcance:**
- **Reconocimiento automático de placas (ANPR/LPR)**. El acceso vehicular se limita al control
  del portón, sin identificación por cámara de matrículas.
- Reconocimiento facial o biometría.
- Domótica/automatización del condominio más allá del portón. El intercomunicador queda fuera:
  el contacto con el propietario es por WhatsApp (RF-20..23).

## Actores / stakeholders

| Actor | Rol |
|---|---|
| **Visitante** | Interactúa con el tótem (voz/texto) para solicitar el acceso. |
| **Residente** | Propietario/inquilino del apartamento; autoriza o rechaza visitas. Para visitantes sin autorización vigente recibe una **solicitud por WhatsApp (vía Soft-IA)** con botones Aprobar/Rechazar (RF-20…23). |
| **Vigilante** | Personal de seguridad; supervisa, atiende excepciones y el botón de pánico. |
| **Administración del condominio** | Gestiona residentes, políticas y autorizaciones en **Soft-IA**. |
| **Soft-IA** | Plataforma de gestión del condominio; fuente de verdad de residentes y autorizaciones (⏳ integración). |

## Estado actual vs objetivo

Existe un **prototipo funcional** end-to-end:

- ✅ Interacción por voz (STT local con Whisper + TTS de navegador) y por texto.
- ✅ Identificación de apartamento/residente y decisión de acceso con **LLM local (Ollama) + RAG
  (ChromaDB)** sobre las políticas del condominio.
- ✅ Respuesta estructurada que dirige el tótem (estado de acceso, acción y animación del avatar).
- ✅ Interfaz del tótem «Videoportero Soft-IA» (horizontal y vertical, día/noche), con el Vigilante como personaje.
- ✅ Despliegue con Docker (frontend + backend) y Ollama nativo en el host.

Pendiente para cumplir el objetivo completo:

- ⏳ **Integración real con Soft-IA** (hoy los datos de residentes son un *mock* local estático).
- ✅ **Escaneo de código QR** real (cámara + jsQR) del QR de invitación de Soft-IA; el QR aporta el
  `id` y la decisión se toma con el **estado real** del libro mayor de autorizaciones
  (`invitations.json`).
- ✅ **Sincronización con Soft-IA** (offline-first): el backend alimenta `apartments.json` e
  `invitations.json` desde los endpoints de Soft-IA y opera contra los archivos locales, para
  verificar accesos **sin conexión constante** (verificado con datos reales).
- ✅ **Registro de visitas en Soft-IA** (RF-14): al autorizar un acceso por QR, la visita se
  registra de vuelta en Soft-IA para auditoría, con cola de reintento si no hay conexión.
- ✅ **Recolección de datos faltantes** antes de autorizar (RF-16..19): si la autorización está
  incompleta, el asistente pide {nombre, cédula, teléfono}; la cédula se lee por cámara con **OCR
  local (Tesseract)** verificando el nombre, y los datos se actualizan en Soft-IA (PATCH).
- 🟡 **Acciones físicas** (portón, botón de pánico) están **simuladas** en el
  frontend; falta integración con hardware real.
- ⏳ **Validación** formal de latencia/tiempos de respuesta/usabilidad mediante simulacros.
- 🟡 **Identidad del condominio como placeholder**: nombre, residentes y políticas son contenido
  de ejemplo ("El Ávila" en el backend, "Valle Blanco" en el frontend) que se **sustituye por el
  condominio real en cada implementación**; la mejora propuesta es hacerla dirigida por
  configuración (RNF-10, ver [requirements.md](requirements.md#3-requerimientos-no-funcionales-rnf)).

## Glosario

| Término | Definición |
|---|---|
| **SoftiaGuard Assistant** | Este proyecto: el asistente de vigilancia virtual de control de acceso. |
| **Vigilante Virtual** | Persona/rol que adopta el asistente al conversar (p. ej. "Vigilante Virtual - Unidad 01"). |
| **Soft-IA** | Software de gestión del condominio Valle Blanco con el que se integra el asistente. |
| **Tótem** | Terminal físico de la entrada donde el visitante interactúa (pantalla, micrófono, altavoz). |
| **LLM local** | Modelo de lenguaje ejecutado localmente vía **Ollama** (sin nube). |
| **RAG** | *Retrieval-Augmented Generation*: recuperación de contexto (datos + políticas) que se inyecta al LLM. |
| **STT / TTS** | *Speech-to-Text* (voz→texto, Whisper local) / *Text-to-Speech* (texto→voz, navegador). |
| **Ollama** | Runtime local open-source para el LLM y los embeddings. |
| **ChromaDB** | Base de datos vectorial embebida usada por el RAG. |
