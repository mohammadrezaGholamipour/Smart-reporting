
from pydantic import BaseModel, Field
from typing import Literal

class ChatRequest(BaseModel):
    query: str = Field(
        min_length=1,
        max_length=4000,
        description="سؤال کاربر درباره اسناد PDF",
    )

    source_id: int | None = Field(
        default=None,
        gt=0,
        description="شناسه سند مورد جست‌وجو؛ اختیاری",
    )

    top_k: int = Field(
        default=3,
        ge=3,
        le=10,
        description="تعداد قطعه‌های متنی برای بازیابی",
    )
    
    retrieval_mode: Literal["embedding", "pageindex"] = Field(
    default="embedding",
    description="روش بازیابی اطلاعات از اسناد",
)
