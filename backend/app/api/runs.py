"""Run + result routes (CONTRACT §4 /runs, /results)."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api._common import get_or_404, page_params, paginate, write_audit
from app.auth import current_account
from app.db import SessionLocal, get_db
from app.engine import execute_run
from app.models import CheckItem, CheckResult, Environment, Run
from app.schemas import (
    CheckResultOut,
    Paginated,
    RunDetail,
    RunOut,
    TriggerRequest,
    TriggerResponse,
)

router = APIRouter(tags=["runs"])


def _execute_run_bg(run_id: int, account: str, env_ids: list[int] | None) -> None:
    """后台执行一次手动巡检（BackgroundTasks；与定时任务同模式）。

    响应返回后 FastAPI 会关闭请求 session（get_db 的 finally），因此这里
    重建独立 session 再执行；run 行已在触发接口由 write_audit commit。
    """
    db = SessionLocal()
    try:
        run = db.get(Run, run_id)
        if run is not None:
            try:
                execute_run(db, run, account, env_ids)
            except Exception:
                # 任何执行期异常都不能让 run 永久停在 running：
                # 标记 failed 并落库后继续上抛（便于日志定位）。
                db.rollback()
                run.status = "failed"
                run.finished_at = datetime.now(timezone.utc)
                db.commit()
                raise
    finally:
        db.close()


@router.post("/runs/trigger", response_model=TriggerResponse)
def trigger_run(
    body: TriggerRequest,
    db: Session = Depends(get_db),
    account: str = Depends(current_account),
    background: BackgroundTasks = BackgroundTasks,
):
    """Create a manual run; inspection executes in the background so the
    request returns immediately and the client polls GET /runs/{id}."""
    if body.scope == "environment" and body.environment_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="environment_id required for scope=environment")
    if body.scope == "check" and body.check_item_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="check_item_id required for scope=check")
    if body.environment_id is not None:
        get_or_404(db, Environment, body.environment_id, "environment")
    if body.check_item_id is not None:
        get_or_404(db, CheckItem, body.check_item_id, "check item")

    run = Run(trigger="manual", triggered_by=account, status="running")
    db.add(run)
    db.flush()
    write_audit(
        db,
        account,
        "run.trigger",
        f"run:{run.id}",
        f"manual trigger scope={body.scope}",
    )
    db.refresh(run)

    # scope narrowing still runs all enabled items (engine resolves targets
    # across all environments); scope is recorded for audit only.
    env_ids = (
        [body.environment_id]
        if (body.scope == "environment" and body.environment_id is not None)
        else None
    )
    background.add_task(_execute_run_bg, run.id, account, env_ids)
    return TriggerResponse(run_id=run.id)


@router.get("/runs", response_model=Paginated)
def list_runs(
    page: dict = Depends(page_params),
    db: Session = Depends(get_db),
    _: str = Depends(current_account),
):
    return paginate(db.query(Run).order_by(Run.id.desc()), page, RunOut)


@router.get("/runs/{run_id}", response_model=RunDetail)
def get_run(
    run_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(current_account),
):
    run = get_or_404(db, Run, run_id, "run")
    rows = (
        db.query(CheckResult.status, func.count(CheckResult.id))
        .filter(CheckResult.run_id == run_id)
        .group_by(CheckResult.status)
        .all()
    )
    counts = {s: n for s, n in rows}
    return RunDetail(
        id=run.id,
        trigger=run.trigger,
        triggered_by=run.triggered_by,
        started_at=run.started_at,
        finished_at=run.finished_at,
        status=run.status,
        progress_note=run.progress_note,
        results=counts,
    )


@router.get("/runs/{run_id}/results", response_model=Paginated)
def get_run_results(
    run_id: int,
    status_filter: str | None = Query(None, alias="status"),
    object_type: str | None = Query(None),
    page: dict = Depends(page_params),
    db: Session = Depends(get_db),
    _: str = Depends(current_account),
):
    get_or_404(db, Run, run_id, "run")
    q = db.query(CheckResult).filter(CheckResult.run_id == run_id)
    if status_filter:
        q = q.filter(CheckResult.status == status_filter)
    if object_type:
        q = q.filter(CheckResult.object_type == object_type)
    return paginate(q.order_by(CheckResult.id), page, CheckResultOut)


@router.get("/results/latest", response_model=Paginated)
def latest_results(
    page: dict = Depends(page_params),
    db: Session = Depends(get_db),
    _: str = Depends(current_account),
):
    """Platform-wide latest run results (aggregated for dashboard)."""
    latest = db.query(Run).order_by(Run.id.desc()).first()
    if not latest:
        return Paginated(items=[], total=0, **page)
    q = db.query(CheckResult).filter(CheckResult.run_id == latest.id).order_by(CheckResult.id)
    return paginate(q, page, CheckResultOut)
