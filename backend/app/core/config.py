from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Smart Reporting API"
    app_env: str = "development"
    debug: bool = True
    api_prefix: str = "/api/v1"

    # Chat model provider (OpenAI-compatible API)
    llm_api_key: str = "ak_d8a28043530a4f14bfbf9073ef45ee6f271c28b39e6148f7"
    llm_base_url: str = "https://api.edrac.ir"
    llm_model: str = "edrac-2"
    
    
    pageindex_dir: str = "../data/pageindex"

    # Embedding endpoint from the supplied cURL example.
    # The API's model field/auth requirements are not confirmed yet.
    embedding_base_url: str = "http://212.80.22.161:8003/v1/embeddings"
    embedding_model: str = "local-embedding-model"
    embedding_api_key: str = ""
    embedding_timeout_seconds: float = 30.0

    # Persistent local storage
    database_url: str = "sqlite:///./data/smart_reporting.db"
    upload_dir: str = "./data/uploads"
    processed_dir: str = "./data/processed"
    chroma_dir: str = "./data/chroma"

    max_upload_mb: int = 25
    allowed_pdf_extensions: str = ".pdf"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
