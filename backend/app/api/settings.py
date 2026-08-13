"""App settings API: runtime configuration of the auto (scheduled) inspection."""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import config, scheduler, settings as kv
from app.api._common import write_audit
from app.auth import current_account
from app.db import get_db

router = APIRouter(prefix="/settings", tags=["settings"])

_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_VALID_DAYS = set(range(7))  # 0=Mon .. 6=Sun


class ScheduleEntry(BaseModel):
    time: str
    days: list[int] = Field(default_factory=list)


class AutoInspectionUpdate(BaseModel):
    enabled: bool | None = None
    schedules: list[ScheduleEntry] | None = None


def _validate_schedules(schedules: list[dict]) -> None:
    for s in schedules:
        if not _TIME_RE.match(s.get("time", "")):
            raise HTTPException(
                status_code=422, detail=f"无效时间点: {s.get('time')}，应为 HH:MM（24 小时制）"
            )
        days = s.get("days", [])
        if not all(int(d) in _VALID_DAYS for d in days):
            raise HTTPException(status_code=422, detail="days 取值须在 0(周一)~6(周日)")
        if len(set(days)) != len(days):
            raise HTTPException(status_code=422, detail="days 不能包含重复项")


@router.get("/auto-inspection")
def get_auto_inspection(
    db: Session = Depends(get_db),
    _: str = Depends(current_account),
):
    return scheduler.get_state(db)


@router.put("/auto-inspection")
def update_auto_inspection(
    body: AutoInspectionUpdate,
    db: Session = Depends(get_db),
    account: str = Depends(current_account),
):
    enabled = (
        body.enabled
        if body.enabled is not None
        else kv.get_bool(db, kv.AUTO_INSPECTION_ENABLED, config.SCHEDULER_ENABLED)
    )
    schedules = (
        [s.model_dump() for s in body.schedules]
        if body.schedules is not None
        else kv.get_schedules(db)
    )
    _validate_schedules(schedules)

    kv.set(db, kv.AUTO_INSPECTION_ENABLED, str(enabled).lower())
    kv.set_schedules(db, schedules)
    scheduler.apply_scheduler(enabled, schedules)
    write_audit(
        db,
        account,
        "scheduler.update",
        "auto_inspection",
        f"enabled={enabled}, schedules={len(schedules)}",
    )
    return scheduler.get_state(db)
