# Backend local — Vigilante Virtual (LLM + RAG, 100% open-source)

Backend de control de acceso para el tótem de **Residencias El Ávila**. Reemplaza la
dependencia de Google Gemini por un **modelo de IA local (Ollama)** con **RAG (ChromaDB)**.
No usa ningún servicio en la nube. La **voz de salida (TTS)** la maneja el navegador; la **voz
de entrada (STT)** se transcribe aquí con **Whisper local**, así que el audio no sale a Internet.

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/verify` | Verificación de acceso (texto → JSON estructurado con LLM + RAG) |
| POST | `/api/transcribe` | STT: recibe un clip de audio y devuelve `{ text }` (Whisper local) |
| GET | `/api/apartments` | Lista los apartamentos (paridad; el frontend no lo usa) |
| GET | `/health` | Estado y modelos configurados |

## Arquitectura

```
Navegador (voz + UI)  ──POST /api/verify─────▶  FastAPI (este backend)
                      ──POST /api/transcribe─▶     │  verify: 1. lookup apartamento (apartments.json)
                                                   │          2. RAG políticas (ChromaDB + bge-m3)
                                                   │          3. LLM Ollama (qwen2.5:7b) → JSON
                                                   │  transcribe: Whisper local (faster-whisper)
                                                   ▼
                                         Ollama (LLM + embeddings, local)
```

## Requisitos

- **Python 3.12+**
- **[Ollama](https://ollama.com)** instalado y corriendo (`ollama serve`).
  En macOS/Apple Silicon o PC con GPU, córrelo nativo para usar la aceleración.

## Puesta en marcha (local)

```bash
# 1. Descargar los modelos locales (una sola vez)
ollama pull qwen2.5:7b-instruct
ollama pull bge-m3

# 2. Instalar dependencias del backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. Configurar entorno
cp .env.example .env        # ajusta OLLAMA_HOST/modelos si hace falta

# 4. Construir el vector store RAG (apartamentos + políticas)
python -m app.ingest

# 5. Arrancar la API
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Vuelve a ejecutar `python -m app.ingest` cada vez que edites `data/apartments.json` o los
documentos de `knowledge/`.

> **STT (Whisper):** el modelo (`WHISPER_MODEL`, por defecto `small`) se **descarga
> automáticamente la primera vez** que se llama a `/api/transcribe` y queda cacheado. En
> Apple Silicon corre en CPU (CTranslate2 no usa Metal), suficiente para clips cortos; en
> Linux con GPU NVIDIA pon `WHISPER_DEVICE=cuda` y `WHISPER_COMPUTE_TYPE=float16`.

## Probar

```bash
curl -s http://localhost:8000/api/verify -H 'Content-Type: application/json' \
  -d '{"message":"Vengo a ver a Valentina","history":[],"currentAptInput":"2B"}' | jq
```

Casos representativos: `2B` → aprobado (`open_gate`); `3A` → denegado (`show_error`);
`4B` + "traigo un código QR" → `show_qr_scanner`; `2A` + "soy repartidor" → autoriza.

## Frontend

El frontend llama a `/api/verify` en el mismo origen. `frontend/server.ts` reenvía `/api/*`
a este backend (variable `BACKEND_URL`, por defecto `http://localhost:8000`). Levanta el
frontend con `npm run dev` dentro de `frontend/`.

## Con Docker (frontend + backend en contenedores)

Ollama corre **nativo en el host** (para usar la GPU/Metal en Apple Silicon); el frontend y el
backend corren en Docker y hablan con él vía `host.docker.internal`.

```bash
# 1. Ollama nativo en el host, con los modelos descargados
ollama serve                       # si no está ya como servicio
ollama pull qwen2.5:7b-instruct    # (una sola vez)
ollama pull bge-m3                 # (una sola vez)

# 2. Levantar frontend + backend en Docker (desde la raíz del repo)
docker compose up --build

# 3. Construir el índice RAG dentro del contenedor backend (primera vez y tras
#    cambiar data/ o knowledge/)
docker compose exec backend python -m app.ingest
```

Abre el tótem en `http://localhost:3000`. El backend queda en `http://localhost:8000`.

> El backend arranca aunque el índice aún no exista (responde sin contexto RAG hasta que
> corras `app.ingest`). Para correr Ollama **también** en Docker (CPU en Mac, GPU NVIDIA en
> Linux), descomenta el servicio `ollama` en `docker-compose.yml` y cambia `OLLAMA_HOST` del
> backend a `http://ollama:11434`.

## Seguridad

Los archivos `.env` originales contenían una `GEMINI_API_KEY` real. Al migrar a local ya no se
usa: **elimínala del repositorio y rótala** en Google AI Studio. `.env` está en `.gitignore`.

## Estructura

```
backend/
  app/
    main.py      # FastAPI: POST /api/verify, GET /api/apartments, /health
    schemas.py   # modelos Pydantic + JSON schema de salida
    config.py    # configuración por entorno
    rag.py       # lookup de apartamentos + recuperación semántica (Chroma)
    ingest.py    # construye el vector store: python -m app.ingest
    prompt.py    # prompt del Vigilante Virtual con contexto RAG inyectado
    llm.py       # llamada a Ollama con salida estructurada
  data/apartments.json      # 8 unidades (1A–4B)
  knowledge/*.md            # políticas y procedimientos (corpus RAG)
```
