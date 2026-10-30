from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import DataSource
from app.schemas.source import SourceRead
from app.services import source_pipeline as pipeline
from app.services.pageindex_service import build_source_index, delete_source_index
from app.services.vector_store import delete_source_chunks
from app.store.db import get_db

router = APIRouter(prefix="/sources", tags=["Sources"])

MAX_UPLOAD_BYTES = settings.max_upload_mb * 1024 * 1024


@router.post("", response_model=SourceRead, status_code=status.HTTP_201_CREATED)
async def upload_source(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    original_name = Path(file.filename or "").name

    if not original_name.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are allowed")

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    stored_path = upload_dir / f"{uuid4().hex}.pdf"
    total_size = 0
    header = b""

    try:
        with stored_path.open("wb") as output:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break

                if not header:
                    header = chunk[:5]

                total_size += len(chunk)
                if total_size > MAX_UPLOAD_BYTES:
                    raise HTTPException(413, "PDF exceeds the maximum upload size")

                output.write(chunk)

        if header != b"%PDF-":
            raise HTTPException(400, "The uploaded file is not a valid PDF")

        source = DataSource(
            name=original_name,
            source_type="pdf",
            original_filename=original_name,
            stored_path=str(stored_path.resolve()),
            status="uploaded",
        )
        db.add(source)
        db.commit()
        db.refresh(source)
        return source

    except Exception:
        db.rollback()
        stored_path.unlink(missing_ok=True)
        raise

    finally:
        await file.close()


@router.get("", response_model=list[SourceRead])
def list_sources(db: Session = Depends(get_db)):
    return db.query(DataSource).order_by(DataSource.created_at.desc()).all()


@router.get("/{source_id}", response_model=SourceRead)
def get_source(source_id: int, db: Session = Depends(get_db)):
    return pipeline.get_source_or_404(db, source_id)


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source(source_id: int, db: Session = Depends(get_db)):
    source = pipeline.get_source_or_404(db, source_id)

    stored_path = Path(source.stored_path) if source.stored_path else None

    try:
        delete_source_chunks(source_id)
    except Exception as exc:
        raise HTTPException(500, "Failed to delete source chunks from vector storage") from exc

    try:
        db.delete(source)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(500, "Failed to delete PDF source from database") from exc

    files = [
        stored_path,
        pipeline.extracted_path(source_id),
        pipeline.chunks_path(source_id),
        pipeline.dashboard_path(source_id),  # قبلاً باقی می‌ماند
    ]
    for path in files:
        if path is not None:
            path.unlink(missing_ok=True)

    delete_source_index(source_id)
    return None


@router.post("/{source_id}/process", response_model=SourceRead)
def process_source(source_id: int, db: Session = Depends(get_db)):
    """مرحلهٔ ۱: استخراج متن و جدول‌ها."""
    source = pipeline.get_source_or_404(db, source_id)
    pipeline.run_extraction(db, source)
    return source


@router.post("/{source_id}/chunk")
def chunk_source(source_id: int, db: Session = Depends(get_db)):
    """مرحلهٔ ۲: قطعه‌بندی متن و جدول‌ها."""
    source = pipeline.get_source_or_404(db, source_id)

    if source.status not in ("processed", "embedded"):
        raise HTTPException(409, "PDF must be processed before chunking")

    chunks = pipeline.run_chunking(db, source)
    return {
        "source_id": source_id,
        "status": "chunked",
        "chunk_count": len(chunks),
        "table_chunk_count": sum(1 for c in chunks if c["kind"] == "table"),
    }


@router.post("/{source_id}/embed")
def embed_source(source_id: int, db: Session = Depends(get_db)):
    """مرحلهٔ ۳: ساخت embedding و ذخیره در ChromaDB."""
    source = pipeline.get_source_or_404(db, source_id)
    count = pipeline.run_embedding(db, source)
    return {
        "source_id": source_id,
        "status": source.status,
        "embedding_count": count,
        "collection": "pdf_chunks",
    }


@router.post("/{source_id}/ingest")
def ingest_source(source_id: int, db: Session = Depends(get_db)):
    """هر سه مرحله (استخراج، قطعه‌بندی، embedding) را یک‌جا اجرا می‌کند."""
    source = pipeline.get_source_or_404(db, source_id)

    pipeline.run_extraction(db, source)
    chunks = pipeline.run_chunking(db, source)
    count = pipeline.run_embedding(db, source, chunks)

    return {
        "source_id": source_id,
        "status": source.status,
        "page_count": source.page_count,
        "chunk_count": len(chunks),
        "embedding_count": count,
    }


@router.post("/{source_id}/pageindex")
def index_source_with_pageindex(source_id: int, db: Session = Depends(get_db)):
    source = pipeline.get_source_or_404(db, source_id)

    if not source.stored_path:
        raise HTTPException(404, "مسیر فایل PDF ثبت نشده است.")

    try:
        return build_source_index(source_id=source.id, pdf_path=source.stored_path)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, f"ساخت ایندکس PageIndex ناموفق بود: {exc}") from exc
