import json
from pathlib import Path
from typing import Any

from pageindex import PageIndexClient

from core.config import settings


def get_pageindex_dir() -> Path:
    """مسیر اصلی ذخیره‌سازی PageIndex."""
    path = Path(settings.pageindex_dir).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_registry_path(source_id: int) -> Path:
    """مسیر فایل نگهداری doc_id هر منبع."""
    registry_dir = get_pageindex_dir() / "registry"
    registry_dir.mkdir(parents=True, exist_ok=True)

    return registry_dir / f"source_{source_id}.json"


def create_pageindex_client() -> PageIndexClient:
    """ساخت کلاینت با تنظیمات مدل فعلی پروژه."""
    if not settings.llm_api_key:
        raise ValueError("LLM_API_KEY تنظیم نشده است.")

    backend = {
        "api_key": settings.llm_api_key,
        "base_url": settings.llm_base_url,
    }

    storage_path = get_pageindex_dir()

    return PageIndexClient(
        index={
            "model": settings.llm_model,
            "backend": backend,
            "storage_path": str(storage_path),
        },
        chat={
            "model": settings.llm_model,
            "backend": backend,
        },
    )


def build_source_index(
    source_id: int,
    pdf_path: str,
) -> dict[str, Any]:
    """ساخت ایندکس PageIndex و ذخیره doc_id برای یک منبع."""
    file_path = Path(pdf_path).resolve()

    if not file_path.is_file():
        raise FileNotFoundError(f"PDF پیدا نشد: {file_path}")

    registry_path = get_registry_path(source_id)

    # اگر قبلاً برای این منبع ایندکس ساخته شده، دوباره نساز.
    if registry_path.is_file():
        with registry_path.open("r", encoding="utf-8") as file:
            saved_data = json.load(file)

        if saved_data.get("doc_id"):
            return {
                "source_id": source_id,
                "doc_id": saved_data["doc_id"],
                "status": "already_indexed",
                "usage": None,
            }

    client = create_pageindex_client()

    result = client.submit_document(
        str(file_path),
        wait=True,
    )

    doc_id = result.get("doc_id")

    if not doc_id:
        raise ValueError("PageIndex شناسهٔ سند را برنگرداند.")

    saved_data = {
        "source_id": source_id,
        "doc_id": doc_id,
        "pdf_path": str(file_path),
        "name": result.get("name", file_path.name),
    }

    registry_path.parent.mkdir(parents=True, exist_ok=True)

    with registry_path.open("w", encoding="utf-8") as file:
        json.dump(
            saved_data,
            file,
            ensure_ascii=False,
            indent=2,
        )

    return {
        "source_id": source_id,
        "doc_id": doc_id,
        "status": "indexed",
        "usage": result.get("usage"),
    }


def get_source_doc_id(source_id: int) -> str | None:
    """خواندن doc_id ذخیره‌شده برای یک منبع."""
    registry_path = get_registry_path(source_id)

    if not registry_path.is_file():
        return None

    with registry_path.open("r", encoding="utf-8") as file:
        saved_data = json.load(file)

    return saved_data.get("doc_id")


def ask_pageindex(source_id: int, question: str) -> dict:
    doc_id = get_source_doc_id(source_id)

    if not doc_id:
        raise ValueError(
            f"برای منبع {source_id} هنوز ایندکس PageIndex ساخته نشده است."
        )

    client = create_pageindex_client()
    result = client.chat(question, doc_id=doc_id)

    return {
        "source_id": source_id,
        "doc_id": doc_id,
        "answer": result,
    }