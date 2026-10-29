
from app.services.embedding_client import embed_texts
from fastapi import APIRouter, Depends, HTTPException
from app.services.vector_store import search_chunks
from app.services.llm_client import generate_answer
from app.schemas.chat import ChatRequest
from sqlalchemy.orm import Session
from app.models import DataSource
from app.store.db import get_db


router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("")
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    query = request.query.strip()

    if not query:
        raise HTTPException(
            status_code=422,
            detail="متن سؤال نمی‌تواند خالی باشد.",
        )

    # اگر کاربر شناسه سند را مشخص کرده، وجود آن را بررسی می‌کنیم.
    if request.source_id is not None:
        source = db.get(DataSource, request.source_id)

        if source is None:
            raise HTTPException(
                status_code=404,
                detail="سند موردنظر پیدا نشد.",
            )

    try:
        # ۱. تبدیل سؤال به بردار عددی
        query_embedding = embed_texts([query])[0]

        # ۲. بازیابی قطعه‌های مرتبط از ChromaDB
        results = search_chunks(
            query_embedding=query_embedding,
            source_id=request.source_id,
            top_k=request.top_k,
        )

        # اگر هیچ قطعه‌ای پیدا نشد، پاسخ حدسی تولید نکن.
        if not results:
            return {
                "query": query,
                "source_id": request.source_id,
                "answer": "اطلاعات مرتبطی برای پاسخ به این سؤال در اسناد پیدا نشد.",
                "sources": [],
            }

        # ۳. آماده‌سازی متن منابع برای مدل زبانی
        context_parts = []

        for result in results:
            metadata = result["metadata"]

            context_parts.append(
                f"[شناسه سند: {metadata['source_id']} | "
                f"صفحه: {metadata['page_number']} | "
                f"قطعه: {metadata['chunk_index']}]\n"
                f"{result['text']}"
            )

        context = "\n\n---\n\n".join(context_parts)

        # ۴. تولید پاسخ بر اساس متن‌های بازیابی‌شده
        answer = generate_answer(
            question=query,
            context=context,
        )

        # ۵. برگرداندن پاسخ و منابع استفاده‌شده
        sources = []

        for result in results:
            metadata = result["metadata"]

            sources.append({
                "source_id": metadata["source_id"],
                "page_number": metadata["page_number"],
                "chunk_index": metadata["chunk_index"],
                "text": result["text"],
                "distance": result["distance"],
            })

        return {
            "query": query,
            "source_id": request.source_id,
            "answer": answer,
            "sources": sources,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"پردازش سؤال با خطا مواجه شد: {exc}",
        ) from exc
