"""Resolving which objects a check item applies to (CONTRACT §6)."""
from __future__ import annotations

from dataclasses import dataclass

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


@dataclass
class TargetObject:
    """A single inspectable object bound to a check item."""

    object_type: str  # physical|service|cluster|pod
    object_name: str
    environment_id: int
    os_flavor: str | None
    address: str | None = None  # SSH-reachable host/IP; None when not mappable
    # 服务探测参数（CONTRACT §3 system_services）；非 service 目标为 None
    probe_mode: str | None = None  # systemd|port|vip
    probe_target: str | None = None  # vip 地址
    probe_port: int | None = None


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
        # 只巡检启用的服务：enabled 是运维显式的停用开关，必须生效
        query = (
            db.query(SystemService, Environment, PhysicalNode)
            .join(Environment, SystemService.environment_id == Environment.id)
            .outerjoin(PhysicalNode, SystemService.node_id == PhysicalNode.id)
            .filter(SystemService.enabled.is_(True))
        )
        for svc, env, node in query:
            targets.append(
                TargetObject(
                    "service",
                    f"{svc.name}@env{env.id}",
                    env.id,
                    _env_flavor(env),
                    node.ip if node else None,
                    probe_mode=svc.probe_mode or "systemd",
                    probe_target=svc.probe_target,
                    probe_port=svc.port,
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


def matches_flavor(check_item: CheckItem, os_flavor: str | None) -> bool:
    """A check item with os_flavor=None applies to all; else exact match."""
    if not check_item.os_flavor:
        return True
    if os_flavor is None:
        return False
    return check_item.os_flavor == os_flavor
