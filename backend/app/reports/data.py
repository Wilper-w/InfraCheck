"""Aggregating a run's results into the numbers a report renders."""
from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import CheckResult, Environment

STATUS_LABEL = {
    "normal": "正常",
    "abnormal": "异常",
    "unreachable": "不可达",
    "failed": "检查失败",
}


def counts(db: Session, run_id: int) -> dict[str, int]:
    rows = (
        db.query(CheckResult.status, func.count(CheckResult.id))
        .filter(CheckResult.run_id == run_id)
        .group_by(CheckResult.status)
        .all()
    )
    out = {"normal": 0, "abnormal": 0, "unreachable": 0, "failed": 0}
    for status, n in rows:
        out[status] = n
    out["total"] = sum(out.values())
    return out


def per_env(db: Session, run_id: int) -> list[dict]:
    envs = db.query(Environment).order_by(Environment.id).all()
    out = []
    for env in envs:
        rows = db.query(CheckResult).filter(
            CheckResult.run_id == run_id, CheckResult.environment_id == env.id
        ).all()
        c = {"normal": 0, "abnormal": 0, "unreachable": 0, "failed": 0}
        for r in rows:
            c[r.status] = c.get(r.status, 0) + 1
        out.append(
            {
                "environment": env.name,
                "os_flavor": env.os_flavor,
                "total": len(rows),
                **c,
            }
        )
    return out


def results_detail(db: Session, run_id: int) -> list[dict]:
    rows = (
        db.query(CheckResult)
        .filter(CheckResult.run_id == run_id)
        .order_by(CheckResult.environment_id, CheckResult.id)
        .all()
    )
    return [
        {
            "object_type": r.object_type,
            "object_name": r.object_name,
            "status": r.status,
            "evidence": r.evidence,
            "os_flavor": r.os_flavor or "all",
        }
        for r in rows
    ]
