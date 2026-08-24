"""Environment, node, service, cluster, namespace, pod routes (CONTRACT §4)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api._common import (
    delete_and_audit,
    get_or_404,
    page_params,
    paginate,
    save_and_audit,
    write_audit,
)
from app.auth import current_account
from app.db import get_db
from app.models import (
    CheckResult,
    Cluster,
    Environment,
    Namespace,
    PhysicalNode,
    Pod,
    SystemService,
)
from app.schemas import (
    ClusterCreate,
    ClusterOut,
    EnvironmentCreate,
    EnvironmentOut,
    EnvironmentSummary,
    EnvironmentUpdate,
    NamespaceCreate,
    NamespaceOut,
    NodeCreate,
    NodeOut,
    Paginated,
    PodCreate,
    PodOut,
    ServiceCreate,
    ServiceOut,
    ServiceUpdate,
)

router = APIRouter(tags=["inventory"])


def _validate_probe(svc: SystemService) -> None:
    """部分更新后重新校验探测参数自洽（ServiceUpdate 各字段独立可选，管不了组合）。"""
    if svc.probe_mode == "port" and svc.port is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="probe_mode=port requires a port")
    if svc.probe_mode == "vip" and not (svc.probe_target or "").strip():
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="probe_mode=vip requires probe_target (the virtual IP)",
        )


# ---------------- environments ----------------
@router.get("/environments", response_model=Paginated)
def list_environments(
    page: dict = Depends(page_params),
    db: Session = Depends(get_db),
    _: str = Depends(current_account),
):
    return paginate(db.query(Environment).order_by(Environment.id), page, EnvironmentOut)


@router.post("/environments", response_model=EnvironmentOut, status_code=201)
def create_environment(
    body: EnvironmentCreate,
    db: Session = Depends(get_db),
    account: str = Depends(current_account),
):
    if db.query(Environment).filter(Environment.name == body.name).first():
        raise HTTPException(status.HTTP_409_CONFLICT, detail="environment name already exists")
    data = body.model_dump()
    env = Environment(**data)
    save_and_audit(db, env, account, "environment.create", f"created {body.name}")
    return EnvironmentOut.model_validate(env)


@router.put("/environments/{env_id}", response_model=EnvironmentOut)
def update_environment(
    env_id: int,
    body: EnvironmentUpdate,
    db: Session = Depends(get_db),
    account: str = Depends(current_account),
):
    env = get_or_404(db, Environment, env_id, "environment")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(env, k, v)
    db.commit()
    db.refresh(env)
    write_audit(db, account, "environment.update", f"environment:{env.id}", f"updated fields: {list(data)}")
    return EnvironmentOut.model_validate(env)


@router.delete("/environments/{env_id}", status_code=204)
def delete_environment(
    env_id: int,
    db: Session = Depends(get_db),
    account: str = Depends(current_account),
):
    env = get_or_404(db, Environment, env_id, "environment")
    delete_and_audit(db, env, account, "environment.delete", f"deleted {env.name}")


@router.get("/environments/{env_id}/summary", response_model=EnvironmentSummary)
def environment_summary(
    env_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(current_account),
):
    env = get_or_404(db, Environment, env_id, "environment")
    # most recent run that has results for this environment
    latest_run = (
        db.query(CheckResult.run_id)
        .filter(CheckResult.environment_id == env_id)
        .order_by(CheckResult.run_id.desc())
        .first()
    )
    counts = {"normal": 0, "abnormal": 0, "unreachable": 0, "failed": 0}
    if latest_run:
        rows = (
            db.query(CheckResult.status, func.count(CheckResult.id))
            .filter(CheckResult.run_id == latest_run[0], CheckResult.environment_id == env_id)
            .group_by(CheckResult.status)
            .all()
        )
        for s, n in rows:
            counts[s] = n
    total = sum(counts.values())
    return EnvironmentSummary(
        environment_id=env.id,
        environment_name=env.name,
        os_flavor=env.os_flavor,
        total=total,
        **counts,
    )


# ---------------- nodes ----------------
@router.get("/environments/{env_id}/nodes", response_model=Paginated)
def list_nodes(
    env_id: int,
    page: dict = Depends(page_params),
    db: Session = Depends(get_db),
    _: str = Depends(current_account),
):
    get_or_404(db, Environment, env_id, "environment")
    q = db.query(PhysicalNode).filter(PhysicalNode.environment_id == env_id).order_by(PhysicalNode.id)
    return paginate(q, page, NodeOut)


@router.post("/environments/{env_id}/nodes", response_model=NodeOut, status_code=201)
def create_node(
    env_id: int,
    body: NodeCreate,
    db: Session = Depends(get_db),
    account: str = Depends(current_account),
):
    env = get_or_404(db, Environment, env_id, "environment")
    node = PhysicalNode(
        environment_id=env_id,
        hostname=body.hostname,
        ip=body.ip,
        os_flavor=body.os_flavor or env.os_flavor,
    )
    save_and_audit(db, node, account, "node.create", f"created {body.hostname}")
    return NodeOut.model_validate(node)


@router.delete("/environments/{env_id}/nodes/{node_id}", status_code=204)
def delete_node(
    env_id: int,
    node_id: int,
    db: Session = Depends(get_db),
    account: str = Depends(current_account),
):
    node = get_or_404(db, PhysicalNode, node_id, "node", environment_id=env_id)
    delete_and_audit(db, node, account, "node.delete", f"deleted {node.hostname}")


# ---------------- services ----------------
@router.get("/environments/{env_id}/services", response_model=Paginated)
def list_services(
    env_id: int,
    page: dict = Depends(page_params),
    db: Session = Depends(get_db),
    _: str = Depends(current_account),
):
    get_or_404(db, Environment, env_id, "environment")
    q = db.query(SystemService).filter(SystemService.environment_id == env_id).order_by(SystemService.id)
    return paginate(q, page, ServiceOut)


@router.post("/environments/{env_id}/services", response_model=ServiceOut, status_code=201)
def create_service(
    env_id: int,
    body: ServiceCreate,
    db: Session = Depends(get_db),
    account: str = Depends(current_account),
):
    get_or_404(db, Environment, env_id, "environment")
    svc = SystemService(
        environment_id=env_id,
        node_id=body.node_id,
        name=body.name,
        port=body.port,
        enabled=body.enabled,
        probe_mode=body.probe_mode,
        probe_target=body.probe_target,
    )
    save_and_audit(db, svc, account, "service.create", f"created {body.name}")
    return ServiceOut.model_validate(svc)


@router.put("/environments/{env_id}/services/{service_id}", response_model=ServiceOut)
def update_service(
    env_id: int,
    service_id: int,
    body: ServiceUpdate,
    db: Session = Depends(get_db),
    account: str = Depends(current_account),
):
    svc = get_or_404(db, SystemService, service_id, "service", environment_id=env_id)
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(svc, k, v)
    _validate_probe(svc)
    db.commit()
    db.refresh(svc)
    write_audit(db, account, "service.update", f"service:{svc.id}", f"updated fields: {list(data)}")
    return ServiceOut.model_validate(svc)


@router.post("/environments/{env_id}/services/{service_id}/toggle", response_model=ServiceOut)
def toggle_service(
    env_id: int,
    service_id: int,
    db: Session = Depends(get_db),
    account: str = Depends(current_account),
):
    """启用/停用。停用后该服务不再进入巡检目标（engine.resolve_targets 过滤）。"""
    svc = get_or_404(db, SystemService, service_id, "service", environment_id=env_id)
    svc.enabled = not svc.enabled
    db.commit()
    db.refresh(svc)
    write_audit(db, account, "service.toggle", f"service:{svc.id}", f"enabled={svc.enabled}")
    return ServiceOut.model_validate(svc)


@router.delete("/environments/{env_id}/services/{service_id}", status_code=204)
def delete_service(
    env_id: int,
    service_id: int,
    db: Session = Depends(get_db),
    account: str = Depends(current_account),
):
    svc = get_or_404(db, SystemService, service_id, "service", environment_id=env_id)
    delete_and_audit(db, svc, account, "service.delete", f"deleted {svc.name}")


# ---------------- clusters ----------------
@router.get("/environments/{env_id}/clusters", response_model=Paginated)
def list_clusters(
    env_id: int,
    page: dict = Depends(page_params),
    db: Session = Depends(get_db),
    _: str = Depends(current_account),
):
    get_or_404(db, Environment, env_id, "environment")
    q = db.query(Cluster).filter(Cluster.environment_id == env_id).order_by(Cluster.id)
    return paginate(q, page, ClusterOut)


@router.post("/environments/{env_id}/clusters", response_model=ClusterOut, status_code=201)
def create_cluster(
    env_id: int,
    body: ClusterCreate,
    db: Session = Depends(get_db),
    account: str = Depends(current_account),
):
    get_or_404(db, Environment, env_id, "environment")
    cluster = Cluster(environment_id=env_id, name=body.name, api_endpoint=body.api_endpoint)
    save_and_audit(db, cluster, account, "cluster.create", f"created {body.name}")
    return ClusterOut.model_validate(cluster)


# ---------------- namespaces ----------------
@router.get("/clusters/{cluster_id}/namespaces", response_model=Paginated)
def list_namespaces(
    cluster_id: int,
    page: dict = Depends(page_params),
    db: Session = Depends(get_db),
    _: str = Depends(current_account),
):
    get_or_404(db, Cluster, cluster_id, "cluster")
    q = db.query(Namespace).filter(Namespace.cluster_id == cluster_id).order_by(Namespace.id)
    return paginate(q, page, NamespaceOut)


@router.post("/clusters/{cluster_id}/namespaces", response_model=NamespaceOut, status_code=201)
def create_namespace(
    cluster_id: int,
    body: NamespaceCreate,
    db: Session = Depends(get_db),
    account: str = Depends(current_account),
):
    get_or_404(db, Cluster, cluster_id, "cluster")
    ns = Namespace(cluster_id=cluster_id, name=body.name)
    save_and_audit(db, ns, account, "namespace.create", f"created {body.name}")
    return NamespaceOut.model_validate(ns)


# ---------------- pods ----------------
@router.get("/namespaces/{ns_id}/pods", response_model=Paginated)
def list_pods(
    ns_id: int,
    page: dict = Depends(page_params),
    db: Session = Depends(get_db),
    _: str = Depends(current_account),
):
    get_or_404(db, Namespace, ns_id, "namespace")
    q = db.query(Pod).filter(Pod.namespace_id == ns_id).order_by(Pod.id)
    return paginate(q, page, PodOut)


@router.post("/namespaces/{ns_id}/pods", response_model=PodOut, status_code=201)
def create_pod(
    ns_id: int,
    body: PodCreate,
    db: Session = Depends(get_db),
    account: str = Depends(current_account),
):
    get_or_404(db, Namespace, ns_id, "namespace")
    pod = Pod(namespace_id=ns_id, name=body.name, labels=body.labels)
    save_and_audit(db, pod, account, "pod.create", f"created {body.name}")
    return PodOut.model_validate(pod)


# ---------------- k8s node auto-discovery ----------------
@router.get("/environments/{env_id}/discover-nodes")
def discover_nodes_report(
    env_id: int,
    db: Session = Depends(get_db),
    account: str = Depends(current_account),
):
    """Dry-run: query the environment's k8s (via gateway) and report nodes that
    would be imported, without writing anything."""
    get_or_404(db, Environment, env_id, "environment")
    from app.discovery import discover_k8s_nodes
    env = db.get(Environment, env_id)
    chain = {
        "host": env.ssh_entry_host or "", "port": env.ssh_entry_port or 22,
        "user": env.ssh_entry_user or "", "master_ip": env.ssh_master_ip or "",
    }
    nodes = discover_k8s_nodes(chain)
    existing = {
        n.hostname
        for n in db.query(PhysicalNode).filter(PhysicalNode.environment_id == env_id)
    }
    return {
        "total": len(nodes),
        "to_import": [n for n in nodes if n["hostname"] not in existing],
        "already_imported": len(existing),
    }


@router.post("/environments/{env_id}/discover-nodes")
def import_discovered_nodes(
    env_id: int,
    db: Session = Depends(get_db),
    account: str = Depends(current_account),
):
    """Run k8s discovery and import nodes into this environment (idempotent)."""
    get_or_404(db, Environment, env_id, "environment")
    from app.api._common import write_audit
    from app.discovery import discover_k8s_nodes, os_flavor_from

    env = db.get(Environment, env_id)
    chain = {
        "host": env.ssh_entry_host or "", "port": env.ssh_entry_port or 22,
        "user": env.ssh_entry_user or "", "master_ip": env.ssh_master_ip or "",
    }
    nodes = discover_k8s_nodes(chain)
    existing = {
        n.hostname for n in db.query(PhysicalNode).filter(PhysicalNode.environment_id == env_id)
    }
    created, skipped = [], 0
    for n in nodes:
        if n["hostname"] in existing:
            skipped += 1
            continue
        db.add(
            PhysicalNode(
                environment_id=env_id,
                hostname=n["hostname"],
                ip=n["ip"],
                os_flavor=os_flavor_from(n["os_image"]) or env.os_flavor,
            )
        )
        created.append(n["hostname"])
    db.commit()
    if created:
        write_audit(db, account, "node.discover", f"env:{env_id}", f"imported {len(created)} k8s nodes")
    return {"imported": created, "count": len(created), "skipped": skipped, "total": len(nodes)}
