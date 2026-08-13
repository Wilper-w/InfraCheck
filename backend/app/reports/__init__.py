"""Report rendering: HTML + Markdown (CONTRACT §4 /reports, §6).

`data` aggregates a run's results; `markdown` and `html` render them; this
module writes both files out and returns the Report row.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app import config
from app.models import Report, Run
from app.reports.data import STATUS_LABEL, counts, per_env, results_detail
from app.reports.html import render_html
from app.reports.markdown import render_markdown

__all__ = [
    "STATUS_LABEL",
    "counts",
    "per_env",
    "results_detail",
    "render_markdown",
    "render_html",
    "generate_report",
]


def generate_report(db: Session, run: Run, account: str) -> Report:
    md = render_markdown(db, run)
    html = render_html(db, run)
    out_dir = config.REPORTS_OUT_DIR
    md_path = out_dir / f"run-{run.id}.md"
    html_path = out_dir / f"run-{run.id}.html"
    md_path.write_text(md, encoding="utf-8")
    html_path.write_text(html, encoding="utf-8")
    return Report(
        run_id=run.id,
        rendered_by=account,
        generated_at=datetime.now(timezone.utc),
        html_path=str(html_path),
        md_path=str(md_path),
    )
