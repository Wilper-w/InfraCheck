"""Run orchestration: fan out check items over targets, persist results (CONTRACT §6)."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app import config
from app.engine.targets import TargetObject, matches_flavor, resolve_targets
from app.models import CheckItem, CheckResult, Run


def select_check_items(db: Session) -> list[CheckItem]:
    """Enabled check items registered by target_type (CONTRACT §6)."""
    return db.query(CheckItem).filter(CheckItem.enabled.is_(True)).order_by(CheckItem.id).all()


def execute_run(db: Session, run: Run, account: str) -> None:
    """Run all enabled check items against their target objects with bounded
    concurrency (asyncio.Semaphore + gather) and persist results.

    The transport (dryrun|ssh) is chosen from config. After results are written,
    a report is generated and audit entries recorded.
    """
    import asyncio

    from app.runner import get_runner
    from app.reports import generate_report
    from app.models import AuditLog

    runner = get_runner(config.RUNNER_TRANSPORT)
    check_items = select_check_items(db)

    jobs: list[tuple[CheckItem, TargetObject]] = []
    for item in check_items:
        for target in resolve_targets(db, item):
            if matches_flavor(item, target.os_flavor):
                jobs.append((item, target))

    # Bounded concurrency (ADR-0002 ~100-200). The semaphore is created INSIDE
    # the coroutine so it binds to the event loop asyncio.run() sets up here,
    # avoiding cross-loop / cross-thread event-loop errors on Python 3.12.
    async def _run_all() -> list[tuple[str, str]]:
        sem = asyncio.Semaphore(config.RUN_CONCURRENCY)

        async def _one(pair: tuple[CheckItem, TargetObject]) -> tuple[str, str]:
            item, target = pair
            async with sem:
                return await runner.execute(item, target)

        return await asyncio.gather(*(_one(p) for p in jobs))

    try:
        outcomes = asyncio.run(_run_all())

        results = [
            CheckResult(
                run_id=run.id,
                check_item_id=item.id,
                object_type=target.object_type,
                object_name=target.object_name,
                environment_id=target.environment_id,
                os_flavor=target.os_flavor,
                status=status,
                evidence=evidence,
                captured_at=datetime.now(timezone.utc),
            )
            for (item, target), (status, evidence) in zip(jobs, outcomes)
        ]
        db.add_all(results)
        run.status = "finished"
        run.finished_at = datetime.now(timezone.utc)
        db.flush()

        # generate report after results are flushed (so report has run id + counts)
        report = generate_report(db, run, account)
        db.add(report)
        db.flush()  # assign report.id before writing the audit target_ref
        db.add(
            AuditLog(
                actor=account,
                action="report.generate",
                target_ref=f"report:{report.id}",
                detail=f"run {run.id} report rendered (html+md)",
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        run.status = "failed"
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        raise


def parse_config(check_item: CheckItem) -> dict:
    try:
        return json.loads(check_item.config) if check_item.config else {}
    except (json.JSONDecodeError, TypeError):
        return {}
