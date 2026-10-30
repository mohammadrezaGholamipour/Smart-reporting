from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ChatMessage, ChatSession
from app.schemas.chat import ChatMessageRead, ChatRequest
from app.services.chat_service import answer_question
from app.store.db import get_db

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("")
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """
    پرسش‌وپاسخ با حافظه. در اولین پیام session_id نفرستید؛ مقدار برگردانده‌شده را
    در پیام‌های بعدی بفرستید تا مدل گفتگوی قبلی (مثلاً «بله» به پیشنهاد قبلی) را بفهمد.
    """
    return answer_question(db, request)


@router.get("/{session_id}", response_model=list[ChatMessageRead])
def get_history(session_id: str, db: Session = Depends(get_db)):
    if db.get(ChatSession, session_id) is None:
        raise HTTPException(404, "گفتگوی موردنظر پیدا نشد.")

    rows = db.scalars(
        select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.id)
    ).all()
    return [ChatMessageRead(role=r.role, content=r.content) for r in rows]


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: str, db: Session = Depends(get_db)):
    session = db.get(ChatSession, session_id)
    if session is None:
        raise HTTPException(404, "گفتگوی موردنظر پیدا نشد.")

    for message in db.scalars(select(ChatMessage).where(ChatMessage.session_id == session_id)):
        db.delete(message)
    db.delete(session)
    db.commit()
    return None
