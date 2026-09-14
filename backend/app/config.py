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
# Libro mayor de autorizaciones del condominio (estado real de cada invitación).
# El QR aporta el id; la decisión se toma según el estado almacenado aquí.
INVITATIONS_FILE: Path = DATA_DIR / "invitations.json"

# Soft-IA: id del condominio destino. Se usa para (1) rechazar códigos QR de otro
# condominio y (2) como parámetro de la sincronización con Soft-IA. Vacío = sin verificar / sin sync.
CONDOMINIO_ID = os.getenv("CONDOMINIO_ID") or None

# --- Sincronización con Soft-IA (alimenta apartments.json e invitations.json) ---
# Los datos se guardan en local para operar sin conexión constante; la sync los
# refresca cada SOFTIA_SYNC_INTERVAL segundos. Deshabilitada por defecto.
def _flag(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")

SOFTIA_ENABLED: bool = _flag("SOFTIA_ENABLED", "false")
SOFTIA_BASE_URL: str = os.getenv("SOFTIA_BASE_URL", "https://php.apiq-soft-ia.orb.local")
SOFTIA_SYNC_INTERVAL: int = int(os.getenv("SOFTIA_SYNC_INTERVAL", "300"))  # segundos
SOFTIA_VERIFY_TLS: bool = _flag("SOFTIA_VERIFY_TLS", "false")  # off en local orb.local

# Login (usuario+contraseña -> token). Rutas/campos configurables (por defecto estilo Lexik JWT).
SOFTIA_LOGIN_PATH: str = os.getenv("SOFTIA_LOGIN_PATH", "/api/login_check")
SOFTIA_USERNAME: str = os.getenv("SOFTIA_USERNAME", "")
SOFTIA_PASSWORD: str = os.getenv("SOFTIA_PASSWORD", "")
SOFTIA_USERNAME_FIELD: str = os.getenv("SOFTIA_USERNAME_FIELD", "username")
SOFTIA_PASSWORD_FIELD: str = os.getenv("SOFTIA_PASSWORD_FIELD", "password")
SOFTIA_TOKEN_FIELD: str = os.getenv("SOFTIA_TOKEN_FIELD", "token")

# Rutas de datos (plantillas; {id} = idcondominio)
SOFTIA_PROPIETARIOS_PATH: str = os.getenv("SOFTIA_PROPIETARIOS_PATH", "/api/condominio/{id}/propietarios")
SOFTIA_AUTORIZACIONES_PATH: str = os.getenv("SOFTIA_AUTORIZACIONES_PATH", "/api/condominio/{id}/autorizaciones")

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
