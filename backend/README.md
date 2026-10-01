# Backend local — Vigilante Virtual (LLM + RAG, 100% open-source)

Backend de control de acceso para el tótem. Reemplaza la
dependencia de servicios en la nube por un **modelo de IA local (Ollama)** con **RAG (ChromaDB)**. La **voz de salida (TTS)** la maneja el navegador; la **voz
de entrada (STT)** se transcribe aquí con **Whisper local**, así que el audio no sale a Internet.

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/verify` | Verificación de acceso (texto → JSON estructurado con LLM + RAG) |
| POST | `/api/verify-qr` | Valida el QR de invitación de Soft-IA: parsea `{ code }`, toma el `id` y decide con el estado real del libro mayor `data/invitations.json` → `VerifyResponse` |
| POST | `/api/transcribe` | STT: recibe un clip de audio y devuelve `{ text }` (Whisper local) |
| POST | `/api/identify` | Identifica por nombre + recoge datos faltantes (nombre/cédula/teléfono) → `GateResponse` |
| POST | `/api/verify-cedula` | OCR local (Tesseract) de la cédula mostrada a la cámara → `{ cedula, match }` |
| POST | `/api/access-request` | Solicitud de acceso al propietario por WhatsApp vía Soft-IA (visitante sin autorización) → `GateResponse` (`await_owner`) |
| GET / DELETE | `/api/access-request/{id}` | Estado de la solicitud (polling del tótem) / cancelarla |
| GET, POST | `/api/dev/access-requests`, `/api/dev/access-request/{id}/respond` | **Solo simulado**: lista pendientes / simula el botón Aprobar-Rechazar del propietario |
| POST | `/api/sync` | Fuerza la sincronización con Soft-IA (propietarios/autorizaciones → JSON local) |
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

Tests (sin Ollama ni Soft-IA; datos aislados en un directorio temporal):

```bash
.venv/bin/python -m pytest -q
```

### Solicitud de acceso por WhatsApp (visitante sin autorización)

Si el visitante no tiene autorización vigente, `/api/identify` pasa a modo solicitud
(`request_mode`), recoge inmueble → nombre → cédula → teléfono → motivo y crea la solicitud.
Con `SOFTIA_SOLICITUD_MOCK=false` (y `SOFTIA_ENABLED=true`) se usa Soft-IA real
(`/api/condominio/{id}/solicitud_acceso`), que envía el WhatsApp al propietario. Para desarrollar
sin Soft-IA, `SOFTIA_SOLICITUD_MOCK=true` (por defecto) simula al propietario con los botones del
banner del tótem o con:

```bash
curl -s http://localhost:8000/api/dev/access-requests | jq        # pendientes
curl -s -X POST http://localhost:8000/api/dev/access-request/<id>/respond \
  -H 'Content-Type: application/json' -d '{"decision":"aprobada"}'  # o "rechazada"
```

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

## Sincronización con Soft-IA (offline-first)

El backend puede alimentar `data/apartments.json` (propietarios) e `data/invitations.json`
(autorizaciones) desde Soft-IA cada `SOFTIA_SYNC_INTERVAL` segundos, y opera contra esos archivos
locales para **verificar accesos aunque no haya conexión**. Si Soft-IA no responde, se conservan
los datos locales.

Además, al **autorizar un acceso por QR** se registra la visita de vuelta en Soft-IA
(`POST /api/condominio/{id}/visitas`, RF-14), en segundo plano; si Soft-IA no responde por red, el
evento se **encola** en `data/pending_visitas.json` y se reintenta en el siguiente ciclo (un rechazo
4xx —vencida/no existe— se descarta).

Configúralo en `.env` (ver `.env.example`): `SOFTIA_ENABLED=true`, `CONDOMINIO_ID=<id>`,
`SOFTIA_BASE_URL`, credenciales de login (`SOFTIA_USERNAME`/`SOFTIA_PASSWORD`) y, si difieren, las
rutas/campos (`SOFTIA_LOGIN_PATH`, `SOFTIA_*_FIELD`, `SOFTIA_*_PATH`, `SOFTIA_VISITAS_PATH`).
`SOFTIA_VERIFY_TLS=false` para el entorno local `orb.local`. `SOFTIA_ENABLED=true` activa la sync
periódica **y** el registro de visitas.

```bash
# Sincronización manual (además de la periódica en segundo plano)
docker compose exec backend python -m app.sync
# o vía HTTP
curl -s -X POST http://localhost:8000/api/sync
```

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
