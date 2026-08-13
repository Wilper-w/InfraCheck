"""Inspection execution engine (CONTRACT §6).

Resolves check-item target objects, dispatches commands per os_flavor, and
produces CheckResult rows. The runner transport (dryrun|ssh) is selected via
RUNNER_TRANSPORT.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app import config
from app.models import (
    CheckItem,
    CheckResult,
    Cluster,
    Environment,
    Namespace,
    PhysicalNode,
    Pod,
    Run,
    SystemService,
)

STATUS_NORMAL = "normal"
STATUS_ABNORMAL = "abnormal"
STATUS_UNREACHABLE = "unreachable"
STATUS_FAILED = "failed"

ALL_STATUSES = (STATUS_NORMAL, STATUS_ABNORMAL, STATUS_UNREACHABLE, STATUS_FAILED)


@dataclass
class TargetObject:
    """A single inspectable object bound to a check item."""

    object_type: str  # physical|service|cluster|pod
    object_name: str
    environment_id: int
    os_flavor: str | None
    address: str | None = None  # SSH-reachable host/IP; None when not mappable


def _env_flavor(env: Environment) -> str:
    return env.os_flavor


def resolve_targets(db: Session, check_item: CheckItem) -> list[TargetObject]:
    """Build the list of target objects a check item applies to (CONTRACT §6)."""
    targets: list[TargetObject] = []
    tt = check_item.target_type

    if tt == "physical":
        query = db.query(PhysicalNode, Environment).join(
            Environment, PhysicalNode.environment_id == Environment.id
        )
        for node, env in query:
            flavor = node.os_flavor or env.os_flavor
            targets.append(
                TargetObject("physical", f"{node.hostname}({node.ip})", env.id, flavor, node.ip)
            )
    elif tt == "service":
        query = (
            db.query(SystemService, Environment, PhysicalNode)
            .join(Environment, SystemService.environment_id == Environment.id)
            .outerjoin(PhysicalNode, SystemService.node_id == PhysicalNode.id)
        )
        for svc, env, node in query:
            targets.append(
                TargetObject(
                    "service",
                    f"{svc.name}@env{env.id}",
                    env.id,
                    _env_flavor(env),
                    node.ip if node else None,
                )
            )
    elif tt == "cluster":
        for cluster, env in (
            db.query(Cluster, Environment)
            .join(Environment, Cluster.environment_id == Environment.id)
            .all()
        ):
            targets.append(
                TargetObject("cluster", cluster.name, env.id, _env_flavor(env))
            )
    elif tt == "pod":
        for pod, ns, cluster, env in (
            db.query(Pod, Namespace, Cluster, Environment)
            .join(Namespace, Pod.namespace_id == Namespace.id)
            .join(Cluster, Namespace.cluster_id == Cluster.id)
            .join(Environment, Cluster.environment_id == Environment.id)
            .all()
        ):
            targets.append(
                TargetObject("pod", f"{ns.name}/{pod.name}", env.id, _env_flavor(env))
            )
    return targets


def _matches_flavor(check_item: CheckItem, os_flavor: str | None) -> bool:
    """A check item with os_flavor=None applies to all; else exact match."""
    if not check_item.os_flavor:
        return True
    if os_flavor is None:
        return False
    return check_item.os_flavor == os_flavor


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
            if _matches_flavor(item, target.os_flavor):
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
