from datetime import datetime, timezone
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.store.db import Base


def utc_now():
    return datetime.now(timezone.utc)


class ReportHistory(Base):
    __tablename__ = "report_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_type: Mapped[str] = mapped_column(String(30), nullable=False, default="text")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="created")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
