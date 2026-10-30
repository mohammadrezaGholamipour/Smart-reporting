import json
from pathlib import Path
from typing import Any

from app.core.config import settings


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


def create_pageindex_client():
    """ساخت کلاینت با تنظیمات مدل فعلی پروژه."""
    # import تنبل: اگر پکیج pageindex نصب نباشد، فقط همین قابلیت خطا می‌دهد
    # و کل برنامه بالا می‌آید.
    try:
        from pageindex import PageIndexClient
    except ImportError as exc:
        raise ValueError(
            "پکیج pageindex نصب نیست؛ برای حالت pageindex آن را نصب کنید "
            "یا retrieval_mode را embedding بگذارید."
        ) from exc

    if not settings.llm_api_key:
        raise ValueError("LLM_API_KEY تنظیم نشده است.")

    backend = {
        "api_key": settings.llm_api_key,
        "base_url": settings.llm_base_url,
    }

    return PageIndexClient(
        index={
            "model": settings.llm_model,
            "backend": backend,
            "storage_path": str(get_pageindex_dir()),
        },
        chat={
            "model": settings.llm_model,
            "backend": backend,
        },
    )


def build_source_index(source_id: int, pdf_path: str) -> dict[str, Any]:
    """ساخت ایندکس PageIndex و ذخیرهٔ doc_id برای یک منبع."""
    file_path = Path(pdf_path).resolve()

    if not file_path.is_file():
        raise FileNotFoundError(f"PDF پیدا نشد: {file_path}")

    registry_path = get_registry_path(source_id)

    if registry_path.is_file():
        saved = json.loads(registry_path.read_text(encoding="utf-8"))
        if saved.get("doc_id"):
            return {
                "source_id": source_id,
                "doc_id": saved["doc_id"],
                "status": "already_indexed",
                "usage": None,
            }

    client = create_pageindex_client()
    result = client.submit_document(str(file_path), wait=True)

    doc_id = result.get("doc_id")
    if not doc_id:
        raise ValueError("PageIndex شناسهٔ سند را برنگرداند.")

    registry_path.write_text(
        json.dumps(
            {
                "source_id": source_id,
                "doc_id": doc_id,
                "pdf_path": str(file_path),
                "name": result.get("name", file_path.name),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return {
        "source_id": source_id,
        "doc_id": doc_id,
        "status": "indexed",
        "usage": result.get("usage"),
    }


def get_source_doc_id(source_id: int) -> str | None:
    registry_path = get_registry_path(source_id)

    if not registry_path.is_file():
        return None

    saved = json.loads(registry_path.read_text(encoding="utf-8"))
    return saved.get("doc_id")


def delete_source_index(source_id: int) -> None:
    """حذف رکورد ایندکس یک منبع (هنگام حذف سند)."""
    get_registry_path(source_id).unlink(missing_ok=True)


def ask_pageindex(source_id: int, question: str) -> dict:
    doc_id = get_source_doc_id(source_id)

    if not doc_id:
        raise ValueError(
            f"برای منبع {source_id} هنوز ایندکس PageIndex ساخته نشده است."
        )

    client = create_pageindex_client()
    result = client.chat(question, doc_id=doc_id)

    return {"source_id": source_id, "doc_id": doc_id, "answer": result}
