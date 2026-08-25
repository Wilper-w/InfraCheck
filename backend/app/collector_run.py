"""Ansible-aggregated execution for a run (scale route for hundreds of nodes).

Replaces per-node nested SSH with a handful of `ansible -m shell` calls on the
gateway (one for physical resource, one per distinct system service), then maps
per-host results back to CheckResults. Called from the executor when
RUNNER_TRANSPORT=ssh and COLLECTOR=ansible, so manual trigger and the scheduler
both use it automatically.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app import collector
from app.checks import resource_script, service_script
from app.engine.status import STATUS_ABNORMAL, STATUS_NORMAL
from app.engine.targets import matches_flavor
from app.models import (
    AuditLog,
    CheckItem,
    CheckResult,
    Environment,
    PhysicalNode,
    Run,
    SystemService,
)


def _evidence(check: str, obj: str, os_flavor: str, rc: int, out: str) -> str:
    return json.dumps(
        {
            "check": check,
            "object": obj,
            "transport": "ansible-fanout",
            "verdict": "pass" if rc == 0 else "threshold_fail",
            "detail": out or "",
            "os_flavor": os_flavor,
        },
        ensure_ascii=False,
    )


def _chain_for(env: Environment) -> dict:
    """Per-environment SSH chain (entry + optional master), falling back to global."""
    return {
        "host": env.ssh_entry_host or "",
        "port": env.ssh_entry_port or 22,
        "user": env.ssh_entry_user or "",
        "master_ip": env.ssh_master_ip or "",
    }


def _run_collect(script: str, nodes: list[PhysicalNode], chain: dict) -> dict[str, tuple[int, str]]:
    collector.sync_inventory([n.ip for n in nodes], chain)
    raw = collector.run_ansible(script, chain)
    return {r["ip"]: (r["rc"], r["out"]) for r in collector.parse_results(raw)}


def execute_run_ansible(
    db: Session,
    run: Run,
    account: str,
    env_ids: list[int] | None = None,
) -> None:
    from app.reports import generate_report
    from app.engine import select_check_items

    check_items = select_check_items(db)
    physical_items = [c for c in check_items if c.target_type == "physical"]
    service_items = [c for c in check_items if c.target_type == "service"]

    envs = (
        db.query(Environment)
        .filter(Environment.id.in_(env_ids) if env_ids else True)
        .order_by(Environment.id)
        .all()
    )
    total = 0

    for idx, env in enumerate(envs, start=1):
        os_flavor = env.os_flavor or "centos"
        nodes = (
            db.query(PhysicalNode).filter(PhysicalNode.environment_id == env.id).all()
        )
        if not nodes:
            continue
        by_ip = {n.ip: n for n in nodes}
        env_results: list[CheckResult] = []

        # physical / all-node checks: resource by default, or a named inspection
        # when the check item's name matches a known all-node check (e.g. bond).
        from app.master_checks import MASTER_CHECK_NAMES, master_script as ms

        for item in physical_items:
            if not matches_flavor(item, os_flavor):
                continue
            chain = _chain_for(env)
            if item.name in MASTER_CHECK_NAMES:
                script = ms(item.name)
            else:
                try:
                    cfg = json.loads(item.config or "{}") if item.config else {}
                except json.JSONDecodeError:
                    cfg = {}
                script = resource_script(cfg, os_flavor)
            rc_by_ip = _run_collect(script, nodes, chain)
            for ip, (rc, out) in rc_by_ip.items():
                n = by_ip.get(ip)
                if not n:
                    continue
                env_results.append(
                    CheckResult(
                        run_id=run.id, check_item_id=item.id,
                        object_type="physical", object_name=f"{n.hostname}({n.ip})",
                        environment_id=env.id, os_flavor=n.os_flavor or os_flavor,
                        status=STATUS_NORMAL if rc == 0 else STATUS_ABNORMAL,
                        evidence=_evidence(item.name, f"{n.hostname}({n.ip})", os_flavor, rc, out),
                        captured_at=datetime.now(timezone.utc),
                    )
                )

        # master-node checks (xunjian.md): DB/etcd-style checks run DIRECTLY on one
        # master (the gateway) — no ansible fan-out — with real output as evidence.
        from app.master_checks import MASTER_CHECK_NAMES, master_script as ms

        master_items = [c for c in check_items if c.target_type == "master"]
        if master_items:
            chain = _chain_for(env)
            gw_ip = collector.gateway_internal_ip(chain)
            gw_node = next((n for n in nodes if n.ip == gw_ip), None) or (nodes[0] if nodes else None)
            if gw_node is not None:
                for item in master_items:
                    if item.name not in MASTER_CHECK_NAMES:
                        continue
                    rc, out = collector.run_on_master(ms(item.name), chain=chain, timeout=120)
                    obj = f"{item.name}@{gw_node.hostname}"
                    env_results.append(
                        CheckResult(
                            run_id=run.id, check_item_id=item.id,
                            object_type="master", object_name=obj,
                            environment_id=env.id, os_flavor=gw_node.os_flavor or os_flavor,
                            status=STATUS_NORMAL if rc == 0 else STATUS_ABNORMAL,
                            evidence=_evidence(item.name, obj, os_flavor or "", rc, out),
                            captured_at=datetime.now(timezone.utc),
                        )
                    )

        # system-service checks: one ansible call per distinct service name
        svc_names = [
            s[0]
            for s in db.query(SystemService.name)
            .filter(SystemService.environment_id == env.id, SystemService.enabled.is_(True))
            .distinct()
        ]
        for name in svc_names:
            rc_by_ip = _run_collect(service_script(name, {}, os_flavor), nodes, chain)
            svc_nodes = (
                db.query(SystemService, PhysicalNode)
                .join(PhysicalNode, SystemService.node_id == PhysicalNode.id)
                .filter(
                    SystemService.environment_id == env.id,
                    SystemService.name == name,
                    SystemService.enabled.is_(True),
                )
                .all()
            )
            for svc, node in svc_nodes:
                hit = rc_by_ip.get(node.ip)
                if hit is None or not node:
                    continue
                rc, out = hit
                env_results.append(
                    CheckResult(
                        run_id=run.id, check_item_id=(service_items[0].id if service_items else 0),
                        object_type="service", object_name=f"{name}@env{env.id}",
                        environment_id=env.id, os_flavor=node.os_flavor or os_flavor,
                        status=STATUS_NORMAL if rc == 0 else STATUS_ABNORMAL,
                        evidence=_evidence(name, f"{name}@env{env.id}", os_flavor, rc, out),
                        captured_at=datetime.now(timezone.utc),
                    )
                )

        # 每个环境巡检完立即落库并更新进度，前端轮询可见实时条数与完成环境数，
        # 而不是等全部环境跑完才一次性提交。
        if env_results:
            total += len(env_results)
            db.add_all(env_results)
            run.progress_note = f"已完成 {idx}/{len(envs)} 个环境 · 累计 {total} 条结果"
            db.commit()

    run.status = "finished"
    run.finished_at = datetime.now(timezone.utc)
    run.progress_note = f"全部 {len(envs)} 个环境完成 · 共 {total} 条结果"
    db.flush()
    report = generate_report(db, run, account)
    db.add(report)
    db.flush()
    db.add(
        AuditLog(actor=account, action="run.trigger", target_ref=f"run:{run.id}",
                 detail=f"ansible-fanout collect ({total} results)")
    )
    db.commit()
