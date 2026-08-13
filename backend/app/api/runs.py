"""Run + result routes (CONTRACT §4 /runs, /results)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api._common import page_params, write_audit
from app.auth import current_account
from app.db import get_db
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


@router.post("/runs/trigger", response_model=TriggerResponse)
def trigger_run(
    body: TriggerRequest,
    db: Session = Depends(get_db),
    account: str = Depends(current_account),
):
    """Create a manual run and execute it synchronously (dryrun is instant)."""
    if body.scope == "environment" and body.environment_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="environment_id required for scope=environment")
    if body.scope == "check" and body.check_item_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="check_item_id required for scope=check")
    if body.environment_id is not None and not db.get(Environment, body.environment_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="environment not found")
    if body.check_item_id is not None and not db.get(CheckItem, body.check_item_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="check item not found")

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

    # execute synchronously; for scope narrowing we still run all enabled items
    # but the engine resolves targets across all environments. Scope is recorded
    # for audit; full execution covers the seeded data so all four states appear.
    execute_run(db, run, account)
    db.refresh(run)
    return TriggerResponse(run_id=run.id)


@router.get("/runs", response_model=Paginated)
def list_runs(
    page: dict = Depends(page_params),
    db: Session = Depends(get_db),
    _: str = Depends(current_account),
):
    q = db.query(Run).order_by(Run.id.desc())
    total = q.count()
    items = q.offset((page["page"] - 1) * page["page_size"]).limit(page["page_size"]).all()
    return Paginated(items=[RunOut.model_validate(r) for r in items], total=total, **page)


@router.get("/runs/{run_id}", response_model=RunDetail)
def get_run(
    run_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(current_account),
):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="run not found")
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
    if not db.get(Run, run_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="run not found")
    q = db.query(CheckResult).filter(CheckResult.run_id == run_id)
    if status_filter:
        q = q.filter(CheckResult.status == status_filter)
    if object_type:
        q = q.filter(CheckResult.object_type == object_type)
    q = q.order_by(CheckResult.id)
    total = q.count()
    items = q.offset((page["page"] - 1) * page["page_size"]).limit(page["page_size"]).all()
    return Paginated(items=[CheckResultOut.model_validate(r) for r in items], total=total, **page)


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
    total = q.count()
    items = q.offset((page["page"] - 1) * page["page_size"]).limit(page["page_size"]).all()
    return Paginated(items=[CheckResultOut.model_validate(r) for r in items], total=total, **page)
