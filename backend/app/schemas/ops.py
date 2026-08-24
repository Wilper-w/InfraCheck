"""Report + audit schemas (CONTRACT §4 /reports, /audit)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    run_id: int
    rendered_by: str
    generated_at: datetime
    html_path: str
    md_path: str
    summary: dict[str, int]


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    actor: str
    action: str
    target_ref: Optional[str] = None
    detail: str
    created_at: datetime
