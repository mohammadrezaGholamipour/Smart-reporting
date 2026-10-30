"""گزارش و داشبورد عمومی برای هر سند PDF."""

import json

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.schemas.dashboard import DashboardRequest, DashboardSpec
from app.services import source_pipeline as pipeline
from app.services.dashboard_service import build_dashboard
from app.store.db import get_db

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post("/{source_id}/dashboard", response_model=DashboardSpec)
def generate_dashboard(
    source_id: int,
    request: DashboardRequest = Body(default_factory=DashboardRequest),
    db: Session = Depends(get_db),
):
    """
    برای هر سندی (فروش، رزومه، قرارداد، گزارش فنی، ...) داشبوردی از KPI، نمودار، جدول و
    تحلیل می‌سازد. در بدنه می‌توانید instruction بدهید تا گزارش روی موضوع خاصی تمرکز کند.
    """
    source = pipeline.get_source_or_404(db, source_id)
    pdf_data = pipeline.load_extracted(db, source)

    try:
        spec = build_dashboard(
            pdf_data,
            instruction=(request.instruction or "").strip() or None,
            use_llm=request.use_llm,
            source_name=source.original_filename or source.name,
        )
    except ValueError as exc:
        raise HTTPException(422, f"ساخت داشبورد ناموفق بود: {exc}") from exc

    pipeline.dashboard_path(source_id).write_text(
        spec.model_dump_json(indent=2), encoding="utf-8"
    )
    return spec


@router.get("/{source_id}/dashboard", response_model=DashboardSpec)
def get_dashboard(source_id: int, db: Session = Depends(get_db)):
    """آخرین داشبورد ساخته‌شده برای این سند."""
    pipeline.get_source_or_404(db, source_id)

    path = pipeline.dashboard_path(source_id)
    if not path.is_file():
        raise HTTPException(404, "هنوز داشبوردی برای این سند ساخته نشده است.")

    return DashboardSpec.model_validate(json.loads(path.read_text(encoding="utf-8")))
