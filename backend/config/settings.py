import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values, load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
BACKEND_ENV_PATH = BACKEND_DIR / ".env"
LEGACY_ENV_PATH = PROJECT_ROOT / ".env"

load_dotenv(BACKEND_ENV_PATH, override=False)

legacy_env = dotenv_values(LEGACY_ENV_PATH)
for legacy_key in ("OLLAMA_MODEL", "OLLAMA_HOST"):
    legacy_value = legacy_env.get(legacy_key)
    if legacy_value:
        os.environ.setdefault(legacy_key, legacy_value)


@dataclass(frozen=True)
class Settings:
    project_root: Path = PROJECT_ROOT
    backend_dir: Path = BACKEND_DIR
    generated_image_dir: Path = PROJECT_ROOT / "uploads" / "generated"
    llm_cache_path: Path = PROJECT_ROOT / "llm_cache.json"
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    huggingface_api_key: str = os.getenv("HUGGINGFACE_API_KEY", "").strip()


settings = Settings()
