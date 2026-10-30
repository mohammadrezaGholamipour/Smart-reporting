
import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# Project root: backend/
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Vercel has a read-only application filesystem.
# Use /tmp for temporary writable storage.
IS_VERCEL = os.getenv("VERCEL") == "1"

if IS_VERCEL:
    DATA_DIR = Path("/tmp/smart-reporting")
else:
    DATA_DIR = BASE_DIR / "data"


class Settings(BaseSettings):
    app_name: str = "Smart Reporting API"
    app_env: str = "development"
    debug: bool = True
    api_prefix: str = "/api/v1"

    # CORS
    cors_origins: str = "*"

    # Chat model provider
    llm_api_key: str = "ak_d8a28043530a4f14bfbf9073ef45ee6f271c28b39e6148f7"
    llm_base_url: str = "https://api.edrac.ir"
    llm_model: str = "edrac-2"
    llm_timeout_seconds: float = 90.0
    llm_json_mode: bool = True
    llm_answer_max_tokens: int = 1500
    llm_dashboard_max_tokens: int = 3000

    # PageIndex
    pageindex_dir: str = str(DATA_DIR / "pageindex")

    # Embedding endpoint
    embedding_base_url: str = "http://212.80.22.161:8003/v1/embeddings"
    embedding_model: str = "local-embedding-model"
    embedding_api_key: str = ""
    embedding_timeout_seconds: float = 30.0

    # Storage
    database_url: str = (
        f"sqlite:///{(DATA_DIR / 'smart_reporting.db').as_posix()}"
    )

    upload_dir: str = str(DATA_DIR / "uploads")
    processed_dir: str = str(DATA_DIR / "processed")
    chroma_dir: str = str(DATA_DIR / "chroma")

    max_upload_mb: int = 25
    allowed_pdf_extensions: str = ".pdf"

    # Chat history
    chat_history_max_messages: int = 10
    chat_history_max_chars: int = 1500

    # Retrieval
    retrieval_max_distance: float = 0.0

    # Dashboard
    dashboard_max_input_chars: int = 14000
    dashboard_max_components: int = 30
    dump_llm_debug: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
