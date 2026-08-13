"""Shared API helpers: pagination params + audit writer."""
from __future__ import annotations

from fastapi import Query

from app.db import Session
from app.models import AuditLog


def page_params(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
):
    return {"page": page, "page_size": page_size}


def write_audit(
    db: Session, actor: str, action: str, target_ref: str | None = None, detail: str = ""
) -> None:
    db.add(AuditLog(actor=actor, action=action, target_ref=target_ref, detail=detail))
    db.commit()
