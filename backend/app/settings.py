"""Key-value app settings helpers (auto-inspection schedules etc.)."""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models import AppSetting

# Well-known keys
AUTO_INSPECTION_ENABLED = "auto_inspection.enabled"  # "true" | "false"
AUTO_INSPECTION_SCHEDULES = "auto_inspection.schedules"  # JSON: [{time:"HH:MM", days:[0..6]}]


def get(db: Session, key: str, default: str | None = None) -> str | None:
    row = db.get(AppSetting, key)
    return row.value if row else default


def set(db: Session, key: str, value: object) -> None:
    """Upsert a setting and persist (commits)."""
    row = db.get(AppSetting, key)
    if row:
        row.value = str(value)
    else:
        db.add(AppSetting(key=key, value=str(value)))
    db.commit()


def get_bool(db: Session, key: str, default: bool) -> bool:
    raw = get(db, key)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def get_schedules(db: Session) -> list[dict]:
    """Parse the schedule list: [{time:"HH:MM", days:[0..6]}]; days empty = every day."""
    raw = get(db, AUTO_INSPECTION_SCHEDULES, None)
    if not raw:
        return []
    try:
        val = json.loads(raw)
        return val if isinstance(val, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def set_schedules(db: Session, schedules: list[dict]) -> None:
    set(db, AUTO_INSPECTION_SCHEDULES, json.dumps(schedules, ensure_ascii=False))
