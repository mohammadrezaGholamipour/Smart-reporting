from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# ریشهٔ پروژه (پوشهٔ بالاتر از app). همهٔ مسیرها نسبت به همین‌جا ساخته می‌شوند
# تا اجرای برنامه از هر پوشه‌ای (ریشه، app و ...) نتیجهٔ یکسان بدهد.
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"


class Settings(BaseSettings):
    app_name: str = "Smart Reporting API"
    app_env: str = "development"
    debug: bool = True
    api_prefix: str = "/api/v1"

    # فرانت‌اند: لیست origin ها با ویرگول جدا شود. "*" یعنی همه.
    cors_origins: str = "*"

    # Chat model provider (OpenAI-compatible API)
    llm_api_key: str = "ak_d8a28043530a4f14bfbf9073ef45ee6f271c28b39e6148f7"
    llm_base_url: str = "https://api.edrac.ir"
    llm_model: str = "edrac-2"
    llm_timeout_seconds: float = 90.0
    llm_json_mode: bool = True  # اگر مدل response_format را پشتیبانی نکرد، خودکار خاموش می‌شود
    llm_answer_max_tokens: int = 1500
    llm_dashboard_max_tokens: int = 3000

    pageindex_dir: str = str(DATA_DIR / "pageindex")

    # Embedding endpoint
    embedding_base_url: str = "http://212.80.22.161:8003/v1/embeddings"
    embedding_model: str = "local-embedding-model"
    embedding_api_key: str = ""
    embedding_timeout_seconds: float = 30.0

    # Persistent local storage
    database_url: str = f"sqlite:///{(DATA_DIR / 'smart_reporting.db').as_posix()}"
    upload_dir: str = str(DATA_DIR / "uploads")
    processed_dir: str = str(DATA_DIR / "processed")
    chroma_dir: str = str(DATA_DIR / "chroma")

    max_upload_mb: int = 25
    allowed_pdf_extensions: str = ".pdf"

    # حافظهٔ گفتگو
    chat_history_max_messages: int = 10  # تعداد پیام‌های قبلی که به مدل داده می‌شود
    chat_history_max_chars: int = 1500   # سقف طول هر پیام قبلی

    # اگر > 0 باشد، قطعه‌هایی که فاصلهٔ کسینوسی‌شان بیشتر از این مقدار است حذف می‌شوند.
    retrieval_max_distance: float = 0.0

    # داشبورد
    dashboard_max_input_chars: int = 14000  # سقف حجم متن سند که به مدل داده می‌شود
    dashboard_max_components: int = 30
    dump_llm_debug: bool = False  # ذخیرهٔ خروجی خام مدل برای عیب‌یابی

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
