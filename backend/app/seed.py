"""Startup seed data (CONTRACT §5). Seeds demo data when DB is empty."""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models import (
    CheckItem,
    Cluster,
    Environment,
    Namespace,
    PhysicalNode,
    Pod,
    SystemService,
)

# Per-environment node counts (env-01..05)
ENV_DEFS = [
    ("env-01", "ubuntu", 4),
    ("env-02", "ubuntu", 3),
    ("env-03", "ubuntu", 3),
    ("env-04", "ubuntu", 3),
    ("env-05", "centos", 3),
]

SERVICES = ["nginx", "keepalived", "mysql", "haproxy"]
# 每个服务按其真实形态选择探测方式（CONTRACT §3 probe_mode）：
# keepalived 不监听端口而是漂 VIP，进程活着但 VIP 不在本机 == 不正常，故用 vip 模式。
SERVICE_PROBES: dict[str, tuple[str, int | None]] = {
    "nginx": ("port", 80),
    "keepalived": ("vip", None),
    "mysql": ("port", 3306),
    "haproxy": ("systemd", 9999),
}

# env-01 gets richer k8s; others get one cluster + default ns + few pods
POD_NAMES = ["etcd", "one-api", "new-api", "redis", "controller", "scheduler"]


def _ip(env_num: int, i: int) -> str:
    return f"10.0.{env_num}.{i}"


def _node_name(env_name: str, i: int) -> str:
    return f"node-{env_name}-{i}"


def seed(db: Session) -> None:
    # Ensure default app settings exist (idempotent, independent of demo env seeding).
    from app import config, settings as kv
    from app.models import AppSetting

    if db.get(AppSetting, kv.AUTO_INSPECTION_ENABLED) is None:
        kv.set(db, kv.AUTO_INSPECTION_ENABLED, str(config.SCHEDULER_ENABLED).lower())
    if db.get(AppSetting, kv.AUTO_INSPECTION_SCHEDULES) is None:
        # default: once daily at 08:00 (every day). days=[] means every day.
        kv.set_schedules(db, [{"time": "08:00", "days": []}])

    if db.query(Environment).count() > 0:
        return

    for idx, (name, os_flavor, node_count) in enumerate(ENV_DEFS, start=1):
        env = Environment(name=name, os_flavor=os_flavor, description=f"演示环境 {name}")
        db.add(env)
        db.flush()

        # nodes
        for i in range(1, node_count + 1):
            db.add(
                PhysicalNode(
                    environment_id=env.id,
                    hostname=_node_name(name, i),
                    ip=_ip(idx, i),
                    os_flavor=os_flavor,
                )
            )
        db.flush()

        # 4 system services, each attached to the first node
        first_node = (
            db.query(PhysicalNode)
            .filter(PhysicalNode.environment_id == env.id)
            .order_by(PhysicalNode.id)
            .first()
        )
        for svc in SERVICES:
            mode, port = SERVICE_PROBES[svc]
            db.add(
                SystemService(
                    environment_id=env.id,
                    node_id=first_node.id if first_node else None,
                    name=svc,
                    port=port,
                    enabled=True,
                    probe_mode=mode,
                    probe_target=f"10.0.{idx}.250" if mode == "vip" else None,
                )
            )

        # clusters
        if name == "env-01":
            cluster = Cluster(
                environment_id=env.id, name="k8s-prod", api_endpoint="https://10.0.1.10:6443"
            )
            db.add(cluster)
            db.flush()
            for ns_name in ("default", "ai", "infra"):
                ns = Namespace(cluster_id=cluster.id, name=ns_name)
                db.add(ns)
                db.flush()
                # 2-3 pods per ns
                pod_pool = POD_NAMES[(ns_name == "default"):][:3] or POD_NAMES[:2]
                for pn in pod_pool:
                    db.add(
                        Pod(
                            namespace_id=ns.id,
                            name=pn,
                            labels=json.dumps({"app": pn, "env": name}),
                        )
                    )
        else:
            cluster = Cluster(
                environment_id=env.id, name=f"k8s-{name}", api_endpoint=f"https://10.0.{idx}.10:6443"
            )
            db.add(cluster)
            db.flush()
            ns = Namespace(cluster_id=cluster.id, name="default")
            db.add(ns)
            db.flush()
            for pn in POD_NAMES[:2]:
                db.add(
                    Pod(
                        namespace_id=ns.id,
                        name=pn,
                        labels=json.dumps({"app": pn, "env": name}),
                    )
                )

    # check items covering all four target types, enabled
    checks = [
        ("节点存活与负载", "physical", None, "检查物理机是否可达及系统负载", {"load_threshold": 4}),
        ("磁盘使用率", "physical", None, "检查根分区磁盘使用率是否超阈值", {"disk_threshold": 85}),
        ("系统服务状态", "service", None, "检查系统服务 systemctl 是否 active", {"expect": "active"}),
        ("K8s 集群连通性", "cluster", None, "检查集群 API 端点连通性", {"timeout": 5}),
        ("Pod 运行状态", "pod", None, "检查 Pod 是否处于 Running 状态", {"expect_phase": "Running"}),
        ("CentOS 节点 systemd", "physical", "centos", "CentOS 专属 systemd 服务检查", {}),
        ("Ubuntu 节点磁盘", "physical", "ubuntu", "Ubuntu 专属磁盘路径检查", {"disk_threshold": 90}),
    ]
    for name, tt, flavor, desc, cfg in checks:
        db.add(
            CheckItem(
                name=name,
                target_type=tt,
                os_flavor=flavor,
                description=desc,
                enabled=True,
                config=json.dumps(cfg),
            )
        )

    db.commit()
