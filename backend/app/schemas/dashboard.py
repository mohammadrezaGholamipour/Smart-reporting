from typing import Annotated, Literal

from pydantic import BaseModel, Field


class DashboardComponentBase(BaseModel):
    id: str
    title: str
    description: str | None = None


class KPIComponent(DashboardComponentBase):
    type: Literal["kpi"] = "kpi"
    value: str | int | float
    unit: str | None = None
    # True: مقدار مستقیماً از متن/جدول سند یا محاسبهٔ پایتون آمده است.
    # False: مدل آن را تولید کرده و در سند پیدا نشده؛ فرانت می‌تواند هشدار نشان بدهد.
    verified: bool | None = None


class ChartComponent(DashboardComponentBase):
    type: Literal["chart"] = "chart"
    chart_type: Literal["line", "bar", "pie", "area"]
    data: list[dict] = Field(default_factory=list)
    x_key: str | None = None
    series: list[str] = Field(default_factory=list)
    verified: bool | None = None


class TableComponent(DashboardComponentBase):
    type: Literal["table"] = "table"
    columns: list[str]
    rows: list[dict]


class TextComponent(DashboardComponentBase):
    type: Literal["text"] = "text"
    content: str


class InsightComponent(DashboardComponentBase):
    type: Literal["insight"] = "insight"
    content: str
    severity: Literal["info", "warning", "critical"] = "info"


DashboardComponent = Annotated[
    KPIComponent | ChartComponent | TableComponent | TextComponent | InsightComponent,
    Field(discriminator="type"),
]


class DashboardSpec(BaseModel):
    title: str
    summary: str | None = None
    components: list[DashboardComponent] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    meta: dict = Field(default_factory=dict)


class DashboardRequest(BaseModel):
    instruction: str | None = Field(
        default=None,
        max_length=1000,
        description=(
            "خواسته‌ٔ اختیاری کاربر برای تمرکز گزارش؛ مثلاً «روی روند فروش و "
            "مقایسهٔ مناطق تمرکز کن» یا «فقط مهارت‌ها را نمودار کن»."
        ),
    )
    use_llm: bool = Field(
        default=True,
        description="اگر false باشد فقط نمودارها و جدول‌های قطعی (بدون مدل زبانی) ساخته می‌شود.",
    )
