"""Ansible-aggregated inspection endpoint: collect across an environment's nodes
in ONE external SSH (fans out on the gateway), writing CheckResults + a report.

This is the scale route for hundreds of nodes — per-node nested SSH is replaced
by a single `ansible all -m shell` over the platform-managed inventory.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import collector
from app.api._common import write_audit
from app.auth import current_account
from app.db import get_db
from app.checks import resource_script
from app.models import AuditLog, CheckItem, CheckResult, Environment, PhysicalNode, Run

router = APIRouter(prefix="/collect", tags=["collect"])


def _first_physical_check_item(db: Session) -> CheckItem | None:
    return (
        db.query(CheckItem)
        .filter(CheckItem.target_type == "physical", CheckItem.enabled.is_(True))
        .order_by(CheckItem.id)
        .first()
    )


@router.post("/physical")
def collect_physical(
    env_id: int,
    limit: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    account: str = Depends(current_account),
):
    env = db.get(Environment, env_id)
    if not env:
        from fastapi import HTTPException, status as st
        raise HTTPException(st.HTTP_404_NOT_FOUND, "environment not found")

    nodes = db.query(PhysicalNode).filter(PhysicalNode.environment_id == env_id).order_by(PhysicalNode.id).all()
    if limit > 0:
        nodes = nodes[:limit]
    if not nodes:
        return {"run_id": None, "error": "no nodes in environment"}

    collector.sync_inventory([n.ip for n in nodes])
    my_ips = {n.ip for n in nodes}
    script = resource_script(
        json.loads((_first_physical_check_item(db).config if _first_physical_check_item(db) else "{}") or "{}"),
        env.os_flavor or "centos",
    )
    raw = collector.run_ansible(script)
    parsed = [r for r in collector.parse_results(raw) if r["ip"] in my_ips]

    # write results in a Run
    check_item = _first_physical_check_item(db)
    run = Run(trigger="manual", triggered_by=account, status="running")
    db.add(run)
    db.flush()

    by_ip = {n.ip: n for n in nodes}
    for r in parsed:
        node = by_ip.get(r["ip"])
        if not node:
            continue
        status = "normal" if r["rc"] == 0 else "abnormal"
        db.add(
            CheckResult(
                run_id=run.id,
                check_item_id=check_item.id if check_item else 0,
                object_type="physical",
                object_name=f"{node.hostname}({node.ip})",
                environment_id=env_id,
                os_flavor=node.os_flavor or env.os_flavor,
                status=status,
                evidence=json.dumps(
                    {
                        "check": check_item.name if check_item else "物理机资源阈值",
                        "object": f"{node.hostname}({node.ip})",
                        "transport": "ansible-fanout",
                        "verdict": "pass" if r["rc"] == 0 else "threshold_fail",
                        "detail": r["out"],
                    },
                    ensure_ascii=False,
                ),
                captured_at=datetime.now(timezone.utc),
            )
        )
    run.status = "finished"
    run.finished_at = datetime.now(timezone.utc)
    db.flush()

    # report + audit
    from app.reports import generate_report
    report = generate_report(db, run, account)
    db.add(report)
    db.flush()
    db.add(
        AuditLog(actor=account, action="run.trigger", target_ref=f"run:{run.id}",
                 detail=f"ansible-fanout collect env={env_id}")
    )
    db.commit()

    normal = sum(1 for r in parsed if r["rc"] == 0)
    import collections
    cnt = collections.Counter(r["rc"] == 0 for r in parsed)
    return {
        "run_id": run.id,
        "environment": env.name,
        "total": len(parsed),
        "normal": cnt.get(True, 0),
        "abnormal": cnt.get(False, 0),
    }
