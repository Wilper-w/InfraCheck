"""Dashboard summary + trend + top-issues routes (CONTRACT §4 /dashboard)."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.auth import current_account
from app.db import get_db
from app.models import CheckResult, Environment, Finding, Run
from app.schemas import (
    DashboardSummary,
    EnvSummaryItem,
    TopIssueItem,
    TrendPoint,
    TrendResponse,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _latest_run_id(db: Session) -> int | None:
    run = db.query(Run).filter(Run.status == "finished").order_by(Run.id.desc()).first()
    if not run:
        run = db.query(Run).order_by(Run.id.desc()).first()
    return run.id if run else None


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(
    db: Session = Depends(get_db),
    _: str = Depends(current_account),
):
    run_id = _latest_run_id(db)
    counts = {"normal": 0, "abnormal": 0, "unreachable": 0, "failed": 0}
    env_items: list[EnvSummaryItem] = []

    envs = db.query(Environment).order_by(Environment.id).all()
    if run_id:
        rows = (
            db.query(CheckResult.status, func.count(CheckResult.id))
            .filter(CheckResult.run_id == run_id)
            .group_by(CheckResult.status)
            .all()
        )
        counts = {s: n for s, n in rows}
        for s in ("normal", "abnormal", "unreachable", "failed"):
            counts.setdefault(s, 0)
        for env in envs:
            env_rows = (
                db.query(CheckResult.status, func.count(CheckResult.id))
                .filter(CheckResult.run_id == run_id, CheckResult.environment_id == env.id)
                .group_by(CheckResult.status)
                .all()
            )
            ec = {s: n for s, n in env_rows}
            et = sum(ec.values())
            env_items.append(
                EnvSummaryItem(
                    environment_id=env.id,
                    name=env.name,
                    os_flavor=env.os_flavor,
                    normal=ec.get("normal", 0),
                    abnormal=ec.get("abnormal", 0),
                    unreachable=ec.get("unreachable", 0),
                    failed=ec.get("failed", 0),
                    total=et,
                )
            )
    else:
        for env in envs:
            env_items.append(
                EnvSummaryItem(environment_id=env.id, name=env.name, os_flavor=env.os_flavor, total=0)
            )

    return DashboardSummary(
        generated_at=datetime.now(timezone.utc),
        total=sum(counts.values()),
        normal=counts.get("normal", 0),
        abnormal=counts.get("abnormal", 0),
        unreachable=counts.get("unreachable", 0),
        failed=counts.get("failed", 0),
        environments=env_items,
    )


@router.get("/top-issues", response_model=list[TopIssueItem])
def dashboard_top_issues(
    limit: int = Query(5, ge=1, le=50),
    db: Session = Depends(get_db),
    _: str = Depends(current_account),
):
    """Top N abnormal/unreachable/failed results from the latest run, for the
    dashboard's actionable drill-down panel (CONTRACT §4 /dashboard)."""
    run_id = _latest_run_id(db)
    if not run_id:
        return []
    rows = (
        db.query(CheckResult, Environment)
        .join(Environment, CheckResult.environment_id == Environment.id)
        .filter(
            CheckResult.run_id == run_id,
            CheckResult.status.in_(["abnormal", "unreachable", "failed"]),
        )
        .order_by(
            case(
                (CheckResult.status == "abnormal", 0),
                (CheckResult.status == "unreachable", 1),
                (CheckResult.status == "failed", 2),
                else_=3,
            ),
            CheckResult.id.desc(),
        )
        .limit(limit)
        .all()
    )
    # Merge triage state from Findings (persist across runs)
    keys = [(r.check_item_id, r.object_type, r.object_name, r.environment_id) for r, _ in rows]
    findings = {}
    if keys:
        for f in db.query(Finding).all():
            findings[(f.check_item_id, f.object_type, f.object_name, f.environment_id)] = f
    return [
        TopIssueItem(
            check_item_id=r.check_item_id,
            object_type=r.object_type,
            object_name=r.object_name,
            environment_id=r.environment_id,
            environment_name=env.name,
            status=r.status,
            evidence=r.evidence or "",
            captured_at=r.captured_at,
            state=finding.state if (finding := findings.get((r.check_item_id, r.object_type, r.object_name, r.environment_id))) else "pending",
            note=finding.note if (finding := findings.get((r.check_item_id, r.object_type, r.object_name, r.environment_id))) else "",
        )
        for r, env in rows
    ]


@router.get("/trend", response_model=TrendResponse)
def dashboard_trend(
    limit: int = Query(30, ge=1, le=200),
    db: Session = Depends(get_db),
    _: str = Depends(current_account),
):
    """每次巡检（一次 run）为一个数据点，展示各次巡检各状态的当次结果数。

    每个点即该次 run 的结果统计，与「最近一次巡检」KPI 口径一致；同一天多次巡检
    会各占一个点，按时间先后排列，取最近 limit 次。
    """
    rows = (
        db.query(
            Run.id.label("run_id"),
            Run.started_at.label("started_at"),
            CheckResult.status,
            func.count(CheckResult.id),
        )
        .join(Run, CheckResult.run_id == Run.id)
        .group_by(Run.id, Run.started_at, CheckResult.status)
        .order_by(Run.started_at.asc(), Run.id.asc())
        .all()
    )
    # 每个 run 一个点，保留出现顺序（已按 started_at、id 升序）
    runs: list[tuple[str, dict[str, int]]] = []
    seen: dict[int, int] = {}
    for run_id, started_at, s, n in rows:
        if run_id not in seen:
            seen[run_id] = len(runs)
            runs.append(
                (started_at.strftime("%Y-%m-%d %H:%M"), {"normal": 0, "abnormal": 0, "unreachable": 0, "failed": 0})
            )
        runs[seen[run_id]][1][s] = n
    series = [TrendPoint(date=label, **counts) for label, counts in runs[-limit:]]
    return TrendResponse(series=series)
