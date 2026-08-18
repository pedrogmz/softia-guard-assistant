"""Configuración central del backend, leída desde variables de entorno (.env)."""
from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv()

# Raíz del paquete backend/ (carpeta que contiene data/, knowledge/, chroma_db/)
BASE_DIR = Path(__file__).resolve().parent.parent

OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
LLM_MODEL: str = os.getenv("LLM_MODEL", "qwen2.5:7b-instruct")
EMBED_MODEL: str = os.getenv("EMBED_MODEL", "bge-m3")

CHROMA_DIR: Path = Path(os.getenv("CHROMA_DIR", BASE_DIR / "chroma_db"))
DATA_DIR: Path = BASE_DIR / "data"
KNOWLEDGE_DIR: Path = BASE_DIR / "knowledge"

APARTMENTS_FILE: Path = DATA_DIR / "apartments.json"

RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "3"))
PORT: int = int(os.getenv("PORT", "8000"))

# --- STT local (Whisper vía faster-whisper) ---
# Tamaños: tiny, base, small, medium, large-v3 (más grande = más preciso y lento)
WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "small")
# cpu (Apple Silicon: CTranslate2 no usa Metal) o cuda (GPU NVIDIA en Linux)
WHISPER_DEVICE: str = os.getenv("WHISPER_DEVICE", "cpu")
# int8 (cpu), float16 (cuda). "int8" da buen equilibrio en CPU.
WHISPER_COMPUTE_TYPE: str = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
# Idioma fijo para el reconocimiento (None = autodetectar)
WHISPER_LANGUAGE: str = os.getenv("WHISPER_LANGUAGE", "es")

# Nombres de las colecciones en ChromaDB
COLLECTION_POLICIES = "politicas_edificio"
