
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(
        min_length=1,
        max_length=4000,
        description="متن سؤال برای جست‌وجوی معنایی",
    )

    source_id: int | None = Field(
        default=None,
        gt=0,
        description="شناسه PDF مورد جست‌وجو؛ اختیاری",
    )

    top_k: int = Field(
        default=3,
        ge=1,
        le=10,
        description="تعداد قطعه‌های متنی بازگشتی",
    )
