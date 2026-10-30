from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from app.services.pageindex_service import build_source_index
from app.services.pdf_processor import extract_pdf_text
from app.services.embedding_client import embed_texts
from app.services.text_chunker import split_text
from app.schemas.source import SourceRead
from datetime import datetime, timezone
from app.core.config import settings
from sqlalchemy.orm import Session
from app.models import DataSource
from app.store.db import get_db
from pathlib import Path
from uuid import uuid4
import json


from app.services.vector_store import (
    store_chunks,
    delete_source_chunks,
)

router = APIRouter(prefix="/sources", tags=["Sources"])

MAX_UPLOAD_BYTES = settings.max_upload_mb * 1024 * 1024


@router.post(
    "",
    response_model=SourceRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_source(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    original_name = Path(file.filename or "").name

    if not original_name.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are allowed")

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    stored_name = f"{uuid4().hex}.pdf"
    stored_path = upload_dir / stored_name
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
                    raise HTTPException(
                        status_code=413,
                        detail="PDF exceeds the maximum upload size",
                    )

                output.write(chunk)

        if header != b"%PDF-":
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is not a valid PDF",
            )

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
def get_source(
    source_id: int,
    db: Session = Depends(get_db),
):
    source = db.get(DataSource, source_id)

    if source is None:
        raise HTTPException(404, "PDF source not found")

    return source

@router.delete(
    "/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_source(
    source_id: int,
    db: Session = Depends(get_db),
):
    source = db.get(DataSource, source_id)

    if source is None:
        raise HTTPException(
            status_code=404,
            detail="PDF source not found",
        )

    stored_path = (
        Path(source.stored_path)
        if source.stored_path
        else None
    )

    processed_dir = Path(settings.processed_dir)

    files_to_delete = [
        processed_dir / f"source_{source_id}.json",
        processed_dir / f"source_{source_id}_chunks.json",
    ]

    # ابتدا قطعات برداری این سند را حذف می‌کنیم.
    try:
        delete_source_chunks(source_id)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to delete source chunks from vector storage",
        ) from exc

    # سپس رکورد منبع را از دیتابیس حذف می‌کنیم.
    try:
        db.delete(source)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to delete PDF source from database",
        ) from exc

    # در پایان، فایل اصلی و فایل‌های پردازش‌شده حذف می‌شوند.
    for path in [stored_path, *files_to_delete]:
        if path is not None:
            path.unlink(missing_ok=True)

    return None

@router.post("/{source_id}/process", response_model=SourceRead)
def process_source(
    source_id: int,
    db: Session = Depends(get_db),
):
    source = db.get(DataSource, source_id)

    if source is None:
        raise HTTPException(404, "PDF source not found")

    if not source.stored_path or not Path(source.stored_path).is_file():
        raise HTTPException(404, "Stored PDF file not found")

    try:
        source.status = "processing"
        source.error_message = None
        db.commit()

        result = extract_pdf_text(source.stored_path)

        output_dir = Path(settings.processed_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / f"source_{source.id}.json"

        with output_path.open("w", encoding="utf-8") as output:
            json.dump(result, output, ensure_ascii=False, indent=2)

        source.page_count = result["page_count"]
        source.processed_at = datetime.now(timezone.utc)
        source.status = "processed"

        db.commit()
        db.refresh(source)

        return source

    except Exception as exc:
        db.rollback()

        source = db.get(DataSource, source_id)
        if source is not None:
            source.status = "failed"
            source.error_message = str(exc)[:2000]
            db.commit()

        raise HTTPException(
            status_code=422,
            detail=f"PDF processing failed: {exc}",
        ) from exc


@router.post("/{source_id}/chunk")
def chunk_source(
    source_id: int,
    db: Session = Depends(get_db),
):
    source = db.get(DataSource, source_id)

    if source is None:
        raise HTTPException(404, "PDF source not found")

    if source.status != "processed":
        raise HTTPException(
            status_code=409,
            detail="PDF must be processed before chunking",
        )

    processed_dir = Path(settings.processed_dir)
    extracted_path = processed_dir / f"source_{source_id}.json"

    if not extracted_path.is_file():
        raise HTTPException(404, "Extracted PDF text not found")

    try:
        with extracted_path.open("r", encoding="utf-8") as file:
            extracted = json.load(file)

        chunks = []

        for page in extracted.get("pages", []):
            page_number = page["page_number"]
            page_text = page.get("text", "")

            page_chunks = split_text(page_text)

            for index, chunk_text in enumerate(page_chunks, start=1):
                chunks.append(
                    {
                        "source_id": source_id,
                        "page_number": page_number,
                        "chunk_index": index,
                        "text": chunk_text,
                    }
                )

        output_path = processed_dir / f"source_{source_id}_chunks.json"

        with output_path.open("w", encoding="utf-8") as file:
            json.dump(
                {
                    "source_id": source_id,
                    "chunk_count": len(chunks),
                    "chunks": chunks,
                },
                file,
                ensure_ascii=False,
                indent=2,
            )

        return {
            "source_id": source_id,
            "status": "chunked",
            "chunk_count": len(chunks),
            "output_file": str(output_path),
        }

    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid extracted PDF data: {exc}",
        ) from exc




@router.post("/{source_id}/embed")
def embed_source(
    source_id: int,
    db: Session = Depends(get_db),
):
    source = db.get(DataSource, source_id)

    if source is None:
        raise HTTPException(404, "PDF source not found")

    chunks_path = (
        Path(settings.processed_dir)
        / f"source_{source_id}_chunks.json"
    )

    if not chunks_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Chunks not found. Run chunking first.",
        )

    try:
        with chunks_path.open("r", encoding="utf-8") as file:
            payload = json.load(file)

        chunks = payload.get("chunks", [])

        if not chunks:
            raise HTTPException(
                status_code=422,
                detail="No text chunks found in this PDF",
            )

        embeddings = embed_texts(
            [chunk["text"] for chunk in chunks]
        )

        count = store_chunks(
            source_id=source_id,
            chunks=chunks,
            embeddings=embeddings,
        )

        # تغییر وضعیت منبع پس از موفقیت ذخیره‌سازی
        source.status = "embedded"
        source.error_message = None
        db.commit()
        db.refresh(source)

        return {
            "source_id": source_id,
            "status": source.status,
            "embedding_count": count,
            "collection": "pdf_chunks",
        }

    except HTTPException:
        raise

    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=502,
            detail=f"Embedding or vector storage failed: {exc}",
        ) from exc



@router.post("/{source_id}/pageindex")
def index_source_with_pageindex(
    source_id: int,
    db: Session = Depends(get_db),
):
    source = db.get(DataSource, source_id)

    if source is None:
        raise HTTPException(
            status_code=404,
            detail="سند موردنظر پیدا نشد.",
        )

    if not source.stored_path:
        raise HTTPException(
            status_code=404,
            detail="مسیر فایل PDF ثبت نشده است.",
        )

    try:
        result = build_source_index(
            source_id=source.id,
            pdf_path=source.stored_path,
        )

        return result

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"ساخت ایندکس PageIndex ناموفق بود: {exc}",
        ) from exc
