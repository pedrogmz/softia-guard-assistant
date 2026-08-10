# Backend local: FastAPI + RAG (ChromaDB) + cliente Ollama.
# El modelo de IA corre en un servicio Ollama aparte (ver docker-compose.yml).
FROM python:3.12-slim

WORKDIR /app

# Dependencias de sistema mínimas para chromadb (compila algunas ruedas)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# La ingesta del vector store se ejecuta aparte (python -m app.ingest);
# aquí solo se arranca la API.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
