from dataclasses import dataclass
import os
from pathlib import Path


def load_dotenv() -> None:
    env_path = Path(".env")
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_path: Path = Path(os.getenv("DATABASE_PATH", "data/chat.db"))
    upload_dir: Path = Path(os.getenv("UPLOAD_DIR", "data/uploads"))
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    openrouter_model: str = os.getenv("OPENROUTER_MODEL", "openrouter/free")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    vector_dir: Path = Path(os.getenv("VECTOR_DIR", "data/index"))
    max_chunk_chars: int = int(os.getenv("MAX_CHUNK_CHARS", "1200"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "150"))


settings = Settings()
