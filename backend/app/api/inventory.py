"""Environment, node, service, cluster, namespace, pod routes (CONTRACT §4)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api._common import page_params, write_audit
from app.auth import current_account
from app.db import get_db
from app.models import (
    CheckResult,
    Cluster,
    Environment,
    Namespace,
    PhysicalNode,
    Pod,
    Run,
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
)

router = APIRouter(tags=["inventory"])


# ---------------- environments ----------------
@router.get("/environments", response_model=Paginated)
def list_environments(
    page: dict = Depends(page_params),
    db: Session = Depends(get_db),
    _: str = Depends(current_account),
):
    q = db.query(Environment).order_by(Environment.id)
    total = q.count()
    items = q.offset((page["page"] - 1) * page["page_size"]).limit(page["page_size"]).all()
    return Paginated(items=[EnvironmentOut.model_validate(e) for e in items], total=total, **page)


@router.post("/environments", response_model=EnvironmentOut, status_code=201)
def create_environment(
    body: EnvironmentCreate,
    db: Session = Depends(get_db),
    account: str = Depends(current_account),
):
    if db.query(Environment).filter(Environment.name == body.name).first():
        raise HTTPException(status.HTTP_409_CONFLICT, detail="environment name already exists")
    env = Environment(name=body.name, os_flavor=body.os_flavor, description=body.description)
    db.add(env)
    db.commit()
    db.refresh(env)
    write_audit(db, account, "environment.create", f"environment:{env.id}", f"created {body.name}")
    return EnvironmentOut.model_validate(env)


@router.put("/environments/{env_id}", response_model=EnvironmentOut)
def update_environment(
    env_id: int,
    body: EnvironmentUpdate,
    db: Session = Depends(get_db),
    account: str = Depends(current_account),
):
    env = db.get(Environment, env_id)
    if not env:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="environment not found")
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
    env = db.get(Environment, env_id)
    if not env:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="environment not found")
    db.delete(env)
    db.commit()
    write_audit(db, account, "environment.delete", f"environment:{env_id}", f"deleted {env.name}")


@router.get("/environments/{env_id}/summary", response_model=EnvironmentSummary)
def environment_summary(
    env_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(current_account),
):
    env = db.get(Environment, env_id)
    if not env:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="environment not found")
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
    if not db.get(Environment, env_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="environment not found")
    q = db.query(PhysicalNode).filter(PhysicalNode.environment_id == env_id).order_by(PhysicalNode.id)
    total = q.count()
    items = q.offset((page["page"] - 1) * page["page_size"]).limit(page["page_size"]).all()
    return Paginated(items=[NodeOut.model_validate(n) for n in items], total=total, **page)


@router.post("/environments/{env_id}/nodes", response_model=NodeOut, status_code=201)
def create_node(
    env_id: int,
    body: NodeCreate,
    db: Session = Depends(get_db),
    account: str = Depends(current_account),
):
    env = db.get(Environment, env_id)
    if not env:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="environment not found")
    node = PhysicalNode(
        environment_id=env_id,
        hostname=body.hostname,
        ip=body.ip,
        os_flavor=body.os_flavor or env.os_flavor,
    )
    db.add(node)
    db.commit()
    db.refresh(node)
    write_audit(db, account, "node.create", f"node:{node.id}", f"created {body.hostname}")
    return NodeOut.model_validate(node)


@router.delete("/environments/{env_id}/nodes/{node_id}", status_code=204)
def delete_node(
    env_id: int,
    node_id: int,
    db: Session = Depends(get_db),
    account: str = Depends(current_account),
):
    node = db.get(PhysicalNode, node_id)
    if not node or node.environment_id != env_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="node not found")
    db.delete(node)
    db.commit()
    write_audit(db, account, "node.delete", f"node:{node_id}", f"deleted {node.hostname}")


# ---------------- services ----------------
@router.get("/environments/{env_id}/services", response_model=Paginated)
def list_services(
    env_id: int,
    page: dict = Depends(page_params),
    db: Session = Depends(get_db),
    _: str = Depends(current_account),
):
    if not db.get(Environment, env_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="environment not found")
    q = db.query(SystemService).filter(SystemService.environment_id == env_id).order_by(SystemService.id)
    total = q.count()
    items = q.offset((page["page"] - 1) * page["page_size"]).limit(page["page_size"]).all()
    return Paginated(items=[ServiceOut.model_validate(s) for s in items], total=total, **page)


@router.post("/environments/{env_id}/services", response_model=ServiceOut, status_code=201)
def create_service(
    env_id: int,
    body: ServiceCreate,
    db: Session = Depends(get_db),
    account: str = Depends(current_account),
):
    if not db.get(Environment, env_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="environment not found")
    svc = SystemService(
        environment_id=env_id,
        node_id=body.node_id,
        name=body.name,
        port=body.port,
        enabled=body.enabled,
    )
    db.add(svc)
    db.commit()
    db.refresh(svc)
    write_audit(db, account, "service.create", f"service:{svc.id}", f"created {body.name}")
    return ServiceOut.model_validate(svc)


@router.delete("/environments/{env_id}/services/{service_id}", status_code=204)
def delete_service(
    env_id: int,
    service_id: int,
    db: Session = Depends(get_db),
    account: str = Depends(current_account),
):
    svc = db.get(SystemService, service_id)
    if not svc or svc.environment_id != env_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="service not found")
    db.delete(svc)
    db.commit()
    write_audit(db, account, "service.delete", f"service:{service_id}", f"deleted {svc.name}")


# ---------------- clusters ----------------
@router.get("/environments/{env_id}/clusters", response_model=Paginated)
def list_clusters(
    env_id: int,
    page: dict = Depends(page_params),
    db: Session = Depends(get_db),
    _: str = Depends(current_account),
):
    if not db.get(Environment, env_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="environment not found")
    q = db.query(Cluster).filter(Cluster.environment_id == env_id).order_by(Cluster.id)
    total = q.count()
    items = q.offset((page["page"] - 1) * page["page_size"]).limit(page["page_size"]).all()
    return Paginated(items=[ClusterOut.model_validate(c) for c in items], total=total, **page)


@router.post("/environments/{env_id}/clusters", response_model=ClusterOut, status_code=201)
def create_cluster(
    env_id: int,
    body: ClusterCreate,
    db: Session = Depends(get_db),
    account: str = Depends(current_account),
):
    if not db.get(Environment, env_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="environment not found")
    cluster = Cluster(
        environment_id=env_id, name=body.name, api_endpoint=body.api_endpoint
    )
    db.add(cluster)
    db.commit()
    db.refresh(cluster)
    write_audit(db, account, "cluster.create", f"cluster:{cluster.id}", f"created {body.name}")
    return ClusterOut.model_validate(cluster)


# ---------------- namespaces ----------------
@router.get("/clusters/{cluster_id}/namespaces", response_model=Paginated)
def list_namespaces(
    cluster_id: int,
    page: dict = Depends(page_params),
    db: Session = Depends(get_db),
    _: str = Depends(current_account),
):
    if not db.get(Cluster, cluster_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="cluster not found")
    q = db.query(Namespace).filter(Namespace.cluster_id == cluster_id).order_by(Namespace.id)
    total = q.count()
    items = q.offset((page["page"] - 1) * page["page_size"]).limit(page["page_size"]).all()
    return Paginated(items=[NamespaceOut.model_validate(n) for n in items], total=total, **page)


@router.post("/clusters/{cluster_id}/namespaces", response_model=NamespaceOut, status_code=201)
def create_namespace(
    cluster_id: int,
    body: NamespaceCreate,
    db: Session = Depends(get_db),
    account: str = Depends(current_account),
):
    if not db.get(Cluster, cluster_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="cluster not found")
    ns = Namespace(cluster_id=cluster_id, name=body.name)
    db.add(ns)
    db.commit()
    db.refresh(ns)
    write_audit(db, account, "namespace.create", f"namespace:{ns.id}", f"created {body.name}")
    return NamespaceOut.model_validate(ns)


# ---------------- pods ----------------
@router.get("/namespaces/{ns_id}/pods", response_model=Paginated)
def list_pods(
    ns_id: int,
    page: dict = Depends(page_params),
    db: Session = Depends(get_db),
    _: str = Depends(current_account),
):
    if not db.get(Namespace, ns_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="namespace not found")
    q = db.query(Pod).filter(Pod.namespace_id == ns_id).order_by(Pod.id)
    total = q.count()
    items = q.offset((page["page"] - 1) * page["page_size"]).limit(page["page_size"]).all()
    return Paginated(items=[PodOut.model_validate(p) for p in items], total=total, **page)


@router.post("/namespaces/{ns_id}/pods", response_model=PodOut, status_code=201)
def create_pod(
    ns_id: int,
    body: PodCreate,
    db: Session = Depends(get_db),
    account: str = Depends(current_account),
):
    if not db.get(Namespace, ns_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="namespace not found")
    pod = Pod(namespace_id=ns_id, name=body.name, labels=body.labels)
    db.add(pod)
    db.commit()
    db.refresh(pod)
    write_audit(db, account, "pod.create", f"pod:{pod.id}", f"created {body.name}")
    return PodOut.model_validate(pod)
