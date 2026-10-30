
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models import DataSource
from app.schemas.chat import ChatRequest
from app.services.embedding_client import embed_texts
from app.services.vector_store import search_chunks
from app.services.llm_client import generate_answer
from app.services.pageindex_service import ask_pageindex
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

    # بررسی وجود سند، در صورت مشخص بودن source_id
    if request.source_id is not None:
        source = db.get(DataSource, request.source_id)

        if source is None:
            raise HTTPException(
                status_code=404,
                detail="سند موردنظر پیدا نشد.",
            )

    # روش اول: پرسش با PageIndex
    if request.retrieval_mode == "pageindex":
        if request.source_id is None:
            raise HTTPException(
                status_code=422,
                detail="برای استفاده از PageIndex باید source_id مشخص شود.",
            )

        try:
            result = ask_pageindex(
                source_id=request.source_id,
                question=query,
            )

            return {
                "query": query,
                "source_id": request.source_id,
                "retrieval_mode": "pageindex",
                "doc_id": result["doc_id"],
                "answer": result["answer"],
                "sources": [],
            }

        except ValueError as exc:
            raise HTTPException(
                status_code=409,
                detail=str(exc),
            ) from exc

        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"پردازش سؤال با PageIndex با خطا مواجه شد: {exc}",
            ) from exc

    # روش دوم: بازیابی مبتنی بر Embedding و ChromaDB
    try:
        # ۱. تبدیل سؤال به بردار عددی
        query_embedding = embed_texts([query])[0]

        # ۲. بازیابی قطعه‌های مرتبط از پایگاه برداری
        results = search_chunks(
            query_embedding=query_embedding,
            source_id=request.source_id,
            top_k=request.top_k,
        )

        # اگر اطلاعات مرتبطی پیدا نشد، پاسخ حدسی تولید نکن
        if not results:
            return {
                "query": query,
                "source_id": request.source_id,
                "retrieval_mode": "embedding",
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

        # ۵. آماده‌سازی منابع استفاده‌شده
        sources = []

        for result in results:
            metadata = result["metadata"]

            sources.append(
                {
                    "source_id": metadata["source_id"],
                    "page_number": metadata["page_number"],
                    "chunk_index": metadata["chunk_index"],
                    "text": result["text"],
                    "distance": result["distance"],
                }
            )

        return {
            "query": query,
            "source_id": request.source_id,
            "retrieval_mode": "embedding",
            "answer": answer,
            "sources": sources,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"پردازش سؤال با Embedding با خطا مواجه شد: {exc}",
        ) from exc
