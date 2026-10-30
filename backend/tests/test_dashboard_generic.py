"""داشبورد باید برای هر موضوعی کار کند، نه فقط فروش."""

import json

from app.services import dashboard_service as ds
from app.services.pdf_processor import extract_pdf_text


def _kinds(spec):
    return [c.type for c in spec.components]


def test_sales_pdf_without_llm(sales_pdf):
    spec = ds.build_dashboard(extract_pdf_text(sales_pdf), use_llm=False)

    assert "kpi" in _kinds(spec) and "chart" in _kinds(spec)
    charts = [c for c in spec.components if c.type == "chart"]
    # ستون‌های با مقیاس بسیار متفاوت (ریال و تعداد) در یک نمودار نیامده‌اند
    assert all(not ({"Revenue (IRR)", "Orders"} <= set(c.series)) for c in charts)
    assert any(c.chart_type == "pie" for c in charts)  # ستون سهم (درصد)
    assert all(c.verified for c in charts)


def test_non_sales_persian_topic_without_llm():
    # جدول نمرات دانشجویان؛ هیچ ارتباطی با فروش ندارد و اعداد فارسی‌اند.
    pdf_data = {
        "page_count": 1,
        "pages": [{"page_number": 1, "text": "کارنامه نیم‌سال اول"}],
        "tables": [
            {
                "page_number": 1,
                "headers": ["درس", "نمره", "واحد"],
                "rows": [
                    ["ریاضی", "۱۷٫۵", 3],
                    ["فیزیک", "۱۴", 3],
                    ["شیمی", "۱۹", 2],
                    ["جمع کل", None, 8],
                ],
            }
        ],
    }
    spec = ds.build_dashboard(pdf_data, use_llm=False)

    chart = next(c for c in spec.components if c.type == "chart")
    assert chart.x_key == "درس"
    values = {p["درس"]: p["نمره"] for p in chart.data}
    assert values == {"ریاضی": 17.5, "فیزیک": 14, "شیمی": 19}  # ردیف جمع کل وارد نمودار نمی‌شود


def test_text_only_document_without_llm_still_returns_something():
    pdf_data = {"pages": [{"page_number": 1, "text": "این یک قرارداد نمونه است."}], "tables": []}
    spec = ds.build_dashboard(pdf_data, use_llm=False)
    assert spec.components and spec.components[0].type == "text"
    assert any("ساختار قابل نمایش" in w for w in spec.warnings)


def test_llm_output_is_sanitized_and_numbers_verified(monkeypatch):
    pdf_data = {
        "page_count": 1,
        "pages": [{"page_number": 1, "text": "Python 80%\nDocker 60%\nLinux 40%"}],
        "tables": [],
    }

    llm_output = {
        "title": "رزومه",
        "summary": "خلاصه",
        "components": [
            {  # معتبر و درست
                "id": "c1", "type": "chart", "title": "مهارت‌ها", "chart_type": "bar",
                "x_key": "skill", "series": ["level"],
                "data": [{"skill": "Python", "level": "80%"}, {"skill": "Docker", "level": 60}],
            },
            {"id": "k1", "type": "kpi", "title": "عدد ساختگی", "value": 999},   # در سند نیست
            {"skill": "Python", "level": 80},                                    # بدون type: حذف
            {"id": "x", "type": "unknown", "title": "نامعتبر"},                   # نوع نامعتبر: حذف
            {"id": "t1", "type": "text", "title": "توضیح", "content": "متن"},
        ],
    }
    monkeypatch.setattr(ds, "generate_json", lambda *a, **k: llm_output)

    spec = ds.build_dashboard(pdf_data)
    by_id = {c.id: c for c in spec.components}

    assert set(by_id) == {"c1", "k1", "t1"}
    assert by_id["c1"].verified is True
    assert by_id["c1"].data[0]["level"] == 80
    assert by_id["k1"].verified is False
    assert any("verified=false" in w for w in spec.warnings)
    assert spec.title == "رزومه"


def test_llm_failure_falls_back_to_deterministic(monkeypatch, sales_pdf):
    def boom(*a, **k):
        raise RuntimeError("model down")

    monkeypatch.setattr(ds, "generate_json", boom)
    spec = ds.build_dashboard(extract_pdf_text(sales_pdf))

    assert spec.meta["llm_used"] is False
    assert any("model down" in w for w in spec.warnings)
    assert "chart" in _kinds(spec)


def test_broken_json_is_repaired():
    from app.services.llm_client import parse_json_object

    broken = '{"title": "گزارش", "components": [{"id": "a", "type": "text", "title": "t", "content": "x"},'
    broken += "\n" * 200
    data = parse_json_object(broken)
    assert data["title"] == "گزارش"
    assert data["components"][0]["id"] == "a"
