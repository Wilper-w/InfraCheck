"""Findings (anomaly triage) API: mark a logical anomaly handled / ignored / reopened."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api._common import write_audit
from app.auth import current_account
from app.db import get_db
from app.models import Finding

router = APIRouter(prefix="/findings", tags=["findings"])

VALID_STATES = {"pending", "resolved", "ignored"}


class FindingUpsert(BaseModel):
    check_item_id: int
    object_type: str
    object_name: str
    environment_id: int
    state: str
    note: str = ""


@router.post("")
def set_finding(
    body: FindingUpsert,
    db: Session = Depends(get_db),
    account: str = Depends(current_account),
):
    if body.state not in VALID_STATES:
        raise HTTPException(status_code=422, detail="state 必须是 pending/resolved/ignored")
    finding = (
        db.query(Finding)
        .filter(
            Finding.check_item_id == body.check_item_id,
            Finding.object_type == body.object_type,
            Finding.object_name == body.object_name,
            Finding.environment_id == body.environment_id,
        )
        .first()
    )
    if finding:
        finding.state = body.state
        finding.note = body.note
        finding.updated_by = account
    else:
        finding = Finding(
            check_item_id=body.check_item_id,
            object_type=body.object_type,
            object_name=body.object_name,
            environment_id=body.environment_id,
            state=body.state,
        )
    db.add(finding)
    db.flush()
    write_audit(
        db,
        account,
        "finding.update",
        f"finding:{finding.id}",
        f"{body.object_name} -> {body.state}",
    )
    return {"id": finding.id, **body.model_dump()}
