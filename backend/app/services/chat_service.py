"""منطق گفتگو: حافظهٔ جلسه، بازنویسی سؤال، بازیابی و تولید پاسخ."""

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import ChatMessage, ChatSession, DataSource
from app.schemas.chat import ChatRequest
from app.services.embedding_client import embed_texts
from app.services.llm_client import generate_answer, rewrite_question
from app.services.pageindex_service import ask_pageindex
from app.services.vector_store import search_chunks

NO_INFO_ANSWER = "اطلاعات مرتبطی برای پاسخ به این سؤال در اسناد پیدا نشد."


# ---------------------------------------------------------
# جلسه و تاریخچه
# ---------------------------------------------------------


def get_or_create_session(
    db: Session, session_id: str | None, source_id: int | None
) -> ChatSession:
    if session_id:
        session = db.get(ChatSession, session_id)
        if session is None:
            raise HTTPException(404, "گفتگوی موردنظر پیدا نشد؛ session_id را خالی بفرستید.")
        return session

    session = ChatSession(source_id=source_id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def load_history(db: Session, session_id: str) -> list[dict]:
    """آخرین پیام‌های جلسه، به ترتیب قدیمی → جدید."""
    rows = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.id.desc())
        .limit(settings.chat_history_max_messages)
    ).all()

    return [{"role": row.role, "content": row.content} for row in reversed(rows)]


def save_turn(db: Session, session: ChatSession, user_text: str, answer: str) -> None:
    db.add(ChatMessage(session_id=session.id, role="user", content=user_text))
    db.add(ChatMessage(session_id=session.id, role="assistant", content=answer))
    session.updated_at = datetime.now(timezone.utc)
    db.commit()


# ---------------------------------------------------------
# پاسخ‌گویی
# ---------------------------------------------------------


def _build_context(results: list[dict]) -> str:
    parts = []
    for item in results:
        meta = item["metadata"]
        kind = "جدول" if meta.get("kind") == "table" else "متن"
        parts.append(
            f"[شناسه سند: {meta['source_id']} | صفحه: {meta['page_number']} | "
            f"قطعه: {meta['chunk_index']} | نوع: {kind}]\n{item['text']}"
        )
    return "\n\n---\n\n".join(parts)


def answer_question(db: Session, request: ChatRequest) -> dict:
    query = request.query.strip()

    if not query:
        raise HTTPException(422, "متن سؤال نمی‌تواند خالی باشد.")

    session = get_or_create_session(db, request.session_id, request.source_id)

    # اگر کاربر source_id نفرستاد ولی جلسه به سندی وصل است، همان سند استفاده می‌شود.
    source_id = request.source_id if request.source_id is not None else session.source_id

    if source_id is not None and db.get(DataSource, source_id) is None:
        raise HTTPException(404, "سند موردنظر پیدا نشد.")

    if session.source_id is None and source_id is not None:
        session.source_id = source_id

    history = load_history(db, session.id)

    # سؤال را با کمک تاریخچه مستقل می‌کنیم؛ این کار باعث می‌شود پیام‌هایی مثل
    # «بله» یا «همونو بساز» هم بازیابی درستی داشته باشند.
    standalone = rewrite_question(history, query)

    base = {
        "query": query,
        "standalone_query": standalone,
        "session_id": session.id,
        "source_id": source_id,
    }

    # ---- روش PageIndex ----
    if request.retrieval_mode == "pageindex":
        if source_id is None:
            raise HTTPException(422, "برای استفاده از PageIndex باید source_id مشخص شود.")

        try:
            result = ask_pageindex(source_id=source_id, question=standalone)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        except Exception as exc:
            raise HTTPException(
                502, f"پردازش سؤال با PageIndex با خطا مواجه شد: {exc}"
            ) from exc

        answer = str(result["answer"])
        save_turn(db, session, query, answer)
        return {
            **base,
            "retrieval_mode": "pageindex",
            "doc_id": result["doc_id"],
            "answer": answer,
            "sources": [],
        }

    # ---- روش Embedding ----
    try:
        query_embedding = embed_texts([standalone])[0]
        results = search_chunks(
            query_embedding=query_embedding,
            source_id=source_id,
            top_k=request.top_k,
        )

        if results:
            context = _build_context(results)
        elif history:
            # پیام پیگیری است و منبع تازه‌ای پیدا نشد؛ از خود گفتگو پاسخ می‌دهیم.
            context = "(منبع جدیدی بازیابی نشد؛ فقط از اطلاعات تاریخچهٔ گفتگو استفاده کن.)"
        else:
            save_turn(db, session, query, NO_INFO_ANSWER)
            return {
                **base,
                "retrieval_mode": "embedding",
                "answer": NO_INFO_ANSWER,
                "sources": [],
            }

        answer = generate_answer(
            question=query,
            context=context,
            history=history,
            standalone_question=standalone,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            502, f"پردازش سؤال با Embedding با خطا مواجه شد: {exc}"
        ) from exc

    save_turn(db, session, query, answer)

    return {
        **base,
        "retrieval_mode": "embedding",
        "answer": answer,
        "sources": [
            {
                "source_id": r["metadata"]["source_id"],
                "page_number": r["metadata"]["page_number"],
                "chunk_index": r["metadata"]["chunk_index"],
                "kind": r["metadata"].get("kind", "text"),
                "text": r["text"],
                "distance": r["distance"],
            }
            for r in results
        ],
    }
