"""Report + audit routes (CONTRACT §4 /reports, /audit)."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse, PlainTextResponse
from sqlalchemy.orm import Session

from app.api._common import get_or_404, page_params, paginate
from app.auth import current_account
from app.db import get_db
from app.models import AuditLog, Report
from app.schemas import AuditLogOut, Paginated, ReportOut

reports_router = APIRouter(prefix="/reports", tags=["reports"])
audit_router = APIRouter(prefix="/audit", tags=["audit"])


# ---------------- reports ----------------
@reports_router.get("", response_model=Paginated)
def list_reports(
    page: dict = Depends(page_params),
    db: Session = Depends(get_db),
    _: str = Depends(current_account),
):
    return paginate(db.query(Report).order_by(Report.id.desc()), page, ReportOut)


@reports_router.get("/{report_id}/html", response_class=HTMLResponse)
def get_report_html(
    report_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(current_account),
):
    report = get_or_404(db, Report, report_id, "report")
    content = Path(report.html_path).read_text(encoding="utf-8") if report.html_path else ""
    return HTMLResponse(content=content)


@reports_router.get("/{report_id}/markdown", response_class=PlainTextResponse)
def get_report_markdown(
    report_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(current_account),
):
    report = get_or_404(db, Report, report_id, "report")
    content = Path(report.md_path).read_text(encoding="utf-8") if report.md_path else ""
    return PlainTextResponse(content=content)


# ---------------- audit ----------------
@audit_router.get("", response_model=Paginated)
def list_audit(
    actor: str | None = Query(None),
    page: dict = Depends(page_params),
    db: Session = Depends(get_db),
    _: str = Depends(current_account),
):
    q = db.query(AuditLog)
    if actor:
        q = q.filter(AuditLog.actor == actor)
    return paginate(q.order_by(AuditLog.id.desc()), page, AuditLogOut)
