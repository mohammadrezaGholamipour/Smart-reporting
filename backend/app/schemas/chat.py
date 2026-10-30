from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(
        min_length=1,
        max_length=4000,
        description="سؤال یا پیام کاربر",
    )

    source_id: int | None = Field(
        default=None,
        gt=0,
        description="شناسه سند مورد جست‌وجو؛ اختیاری",
    )

    session_id: str | None = Field(
        default=None,
        max_length=32,
        description=(
            "شناسهٔ گفتگو. در اولین پیام خالی بگذارید؛ پاسخ یک session_id برمی‌گرداند "
            "و برای پیام‌های بعدی همان را بفرستید تا مدل پیام‌های قبلی را به خاطر داشته باشد."
        ),
    )

    top_k: int = Field(
        default=4,
        ge=1,
        le=10,
        description="تعداد قطعه‌های متنی برای بازیابی",
    )

    retrieval_mode: Literal["embedding", "pageindex"] = Field(
        default="embedding",
        description="روش بازیابی اطلاعات از اسناد",
    )


class ChatMessageRead(BaseModel):
    role: str
    content: str
