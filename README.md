# SoftiaGuard Assistant — Tótem de control de acceso con IA local

Chatbot de control de acceso para el conjunto residencial **Residencias El Ávila**. El visitante
se acerca al tótem de la entrada, **habla o escribe** lo que desea (p. ej. *"Quiero visitar el
2B"*) y el **Vigilante Virtual** le responde **por voz**, decidiendo si abre el portón, llama al
residente, pide un código QR o niega el acceso.

Todo el procesamiento de IA es **local y open-source**: no depende de ningún servicio en la nube.

## Arquitectura

```
Navegador (voz + UI 3D)                Docker                         Host
┌─────────────────────┐        ┌──────────────────────┐      ┌──────────────────────┐
│  frontend (React)    │        │  frontend  :3000     │      │  Ollama (nativo)     │
│  Web Speech API      │──/api─▶│   proxy /api ───────────────▶  backend :8000       │
│  (TTS voz + STT mic) │        │  backend   :8000     │──────▶  LLM  qwen2.5:7b     │
└─────────────────────┘        │   FastAPI + RAG      │ 11434│  Embed bge-m3        │
                                └──────────────────────┘      └──────────────────────┘
```

- **Voz de salida (TTS)**: la síntesis ocurre **en el navegador** (Web Speech API).
- **Voz de entrada (STT)**: el navegador graba un clip y lo envía a `/api/transcribe`, donde
  **Whisper local** (faster-whisper) lo transcribe. El audio **no sale a ningún servicio externo**.
- **LLM local**: [Ollama](https://ollama.com) con `qwen2.5:7b-instruct` (respuesta en JSON estructurado).
- **RAG local**: ChromaDB (embebido) + embeddings `bge-m3` sobre la base de conocimiento
  (apartamentos + políticas del edificio).
- **Ollama corre nativo en el host** para aprovechar la GPU/Metal (en macOS la GPU no está
  disponible dentro de Docker). El frontend y el backend corren en contenedores y hablan con
  Ollama vía `host.docker.internal`.

## Requisitos previos

| Herramienta | Uso |
|---|---|
| [Docker](https://www.docker.com/) + Docker Compose | Levantar frontend y backend |
| [Ollama](https://ollama.com) | Servir el modelo de IA local (LLM + embeddings) |

## Puesta en marcha

### 1. Arrancar Ollama y descargar los modelos (en el host)

```bash
ollama serve                       # si no está ya corriendo como servicio
ollama pull qwen2.5:7b-instruct    # modelo LLM (~4.7 GB)
ollama pull bge-m3                 # modelo de embeddings multilingüe (~1.2 GB)
```

> Los modelos se descargan **una sola vez** y quedan cacheados en el host.

### 2. Construir y levantar los contenedores

Desde la raíz del repositorio (donde está `docker-compose.yml`):

```bash
docker compose up --build
```

Esto levanta:
- **frontend** en http://localhost:3000
- **backend** en http://localhost:8000

### 3. Construir el índice RAG (primera vez)

Con los contenedores arriba, en otra terminal:

```bash
docker compose exec backend python -m app.ingest
```

Indexa los apartamentos (`backend/data/apartments.json`) y las políticas
(`backend/knowledge/*.md`) en ChromaDB. El índice **persiste** en `./data/` (montado como
volumen), así que no hay que repetirlo en cada arranque — solo cuando cambies esos datos.

> El backend arranca aunque el índice aún no exista: responde sin contexto RAG hasta que
> ejecutes este paso.

### 4. Usar el tótem

Abre **http://localhost:3000** y prueba, por voz o texto:
- *"Vengo a ver a Valentina"* / teclea `2B` → acceso aprobado, abre el portón.
- *"Voy al 3A"* → denegado (propietario fuera de la ciudad).
- *"Traigo un código QR para el 4B"* → pide escanear el QR.
- *"Soy repartidor, voy al 2A"* → autoriza el delivery.

## Comandos útiles

```bash
docker compose logs -f backend        # ver logs del backend
docker compose exec backend python -m app.ingest   # reconstruir el índice RAG
docker compose down                   # detener y eliminar los contenedores
docker compose up --build -d          # levantar en segundo plano
curl -s http://localhost:8000/health  # comprobar el backend
```

Probar el backend directamente:

```bash
curl -s http://localhost:8000/api/verify -H 'Content-Type: application/json' \
  -d '{"message":"Vengo a ver a Valentina","history":[],"currentAptInput":"2B"}'
```

## Estructura del repositorio

```
SoftiaGuardAssistant/
├── docker-compose.yml     # orquesta frontend + backend (Ollama va nativo en el host)
├── data/                  # índice RAG persistido (ChromaDB) — se genera con app.ingest
├── backend/               # API local: FastAPI + Ollama + RAG (ver backend/README.md)
│   ├── app/               # main.py, rag.py, ingest.py, llm.py, prompt.py, schemas.py
│   ├── data/apartments.json
│   └── knowledge/*.md     # políticas y procedimientos (corpus RAG)
└── frontend/              # UI React + Vite (tótem «Videoportero Soft-IA»); proxya /api al backend
```

Detalle del backend y su configuración: [backend/README.md](backend/README.md).

## Configuración

Variables principales (definidas en `docker-compose.yml`, ajustables):

| Variable | Servicio | Por defecto | Descripción |
|---|---|---|---|
| `OLLAMA_HOST` | backend | `http://host.docker.internal:11434` | Dónde corre Ollama |
| `LLM_MODEL` | backend | `qwen2.5:7b-instruct` | Modelo de lenguaje |
| `EMBED_MODEL` | backend | `bge-m3` | Modelo de embeddings |
| `WHISPER_MODEL` | backend | `small` | Modelo de STT (Whisper) |
| `BACKEND_URL` | frontend | `http://backend:8000` | Destino del proxy `/api` |

Para correr **Ollama también en Docker** (CPU en Mac, GPU NVIDIA en Linux), descomenta el
servicio `ollama` al final de `docker-compose.yml` y cambia `OLLAMA_HOST` a `http://ollama:11434`.

## Solución de problemas

- **`Backend proxy error: fetch failed`**: el proxy no alcanza al backend. En Docker, el
  frontend usa `BACKEND_URL=http://backend:8000`. Fuera de Docker, usa `127.0.0.1` (no
  `localhost`, que Node resuelve a IPv6 mientras uvicorn escucha en IPv4).
- **El backend no responde con contexto / respuestas genéricas**: falta construir el índice →
  `docker compose exec backend python -m app.ingest`.
- **Errores de conexión a Ollama**: verifica que `ollama serve` esté corriendo en el host y que
  los modelos estén descargados (`ollama list`).
- **La voz no suena**: la síntesis depende de las voces del navegador/SO instaladas para
  español; en Chrome/Edge suele funcionar sin configuración.
- **El micrófono no funciona / `getUserMedia` falla**: requiere **contexto seguro**. Funciona en
  `http://localhost:3000`, pero si accedes al tótem por IP o dominio necesitas **HTTPS**.
- **La primera transcripción tarda**: Whisper descarga el modelo (`small`, ~0.5 GB) la primera
  vez y lo cachea en el volumen `whisper_cache`; las siguientes son rápidas.

## Seguridad

Los archivos `.env` originales del proyecto contenían una `GEMINI_API_KEY` real (del backend
anterior basado en la nube). Ya **no se usa**: conviene **eliminarla del repositorio y rotarla**.
Los `.env` están en `.gitignore`.
