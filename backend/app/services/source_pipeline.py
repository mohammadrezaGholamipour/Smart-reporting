"""مراحل پردازش یک سند (استخراج → قطعه‌بندی → embedding) به‌صورت توابع مشترک."""

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import DataSource
from app.services.embedding_client import embed_texts
from app.services.pdf_processor import extract_pdf_text
from app.services.text_chunker import build_chunks
from app.services.vector_store import store_chunks


def processed_path(source_id: int, suffix: str = "") -> Path:
    directory = Path(settings.processed_dir)
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"source_{source_id}{suffix}.json"


def extracted_path(source_id: int) -> Path:
    return processed_path(source_id)


def chunks_path(source_id: int) -> Path:
    return processed_path(source_id, "_chunks")


def dashboard_path(source_id: int) -> Path:
    return processed_path(source_id, "_dashboard")


def get_source_or_404(db: Session, source_id: int) -> DataSource:
    source = db.get(DataSource, source_id)
    if source is None:
        raise HTTPException(404, "سند موردنظر پیدا نشد.")
    return source


def run_extraction(db: Session, source: DataSource) -> dict:
    """استخراج متن و جدول‌ها؛ نتیجه روی دیسک ذخیره و وضعیت سند به‌روز می‌شود."""
    if not source.stored_path or not Path(source.stored_path).is_file():
        raise HTTPException(404, "فایل PDF این سند پیدا نشد.")

    try:
        source.status = "processing"
        source.error_message = None
        db.commit()

        result = extract_pdf_text(source.stored_path)

        extracted_path(source.id).write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        source.page_count = result["page_count"]
        source.processed_at = datetime.now(timezone.utc)
        source.status = "processed"
        db.commit()
        db.refresh(source)
        return result

    except Exception as exc:
        db.rollback()
        source = db.get(DataSource, source.id)
        if source is not None:
            source.status = "failed"
            source.error_message = str(exc)[:2000]
            db.commit()
        raise HTTPException(422, f"PDF processing failed: {exc}") from exc


def load_extracted(db: Session, source: DataSource) -> dict:
    """داده‌ی استخراج‌شده را می‌خواند؛ اگر هنوز استخراج نشده، خودکار استخراج می‌کند."""
    path = extracted_path(source.id)
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass  # فایل خراب است؛ دوباره استخراج می‌شود
    return run_extraction(db, source)


def run_chunking(db: Session, source: DataSource) -> list[dict]:
    extracted = load_extracted(db, source)
    chunks = build_chunks(extracted, source.id)

    chunks_path(source.id).write_text(
        json.dumps(
            {"source_id": source.id, "chunk_count": len(chunks), "chunks": chunks},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return chunks


def run_embedding(db: Session, source: DataSource, chunks: list[dict] | None = None) -> int:
    if chunks is None:
        path = chunks_path(source.id)
        if not path.is_file():
            raise HTTPException(404, "Chunks not found. Run chunking first.")
        chunks = json.loads(path.read_text(encoding="utf-8")).get("chunks", [])

    if not chunks:
        raise HTTPException(422, "No text chunks found in this PDF")

    try:
        embeddings = embed_texts([c["text"] for c in chunks])
        count = store_chunks(source_id=source.id, chunks=chunks, embeddings=embeddings)
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(502, f"Embedding or vector storage failed: {exc}") from exc

    source.status = "embedded"
    source.error_message = None
    db.commit()
    db.refresh(source)
    return count
