"""SQLAlchemy ORM models (CONTRACT §3)."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Environment(Base):
    __tablename__ = "environments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    os_flavor: Mapped[str] = mapped_column(String(32), nullable=False)  # ubuntu|centos
    description: Mapped[str] = mapped_column(String(512), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    nodes: Mapped[list["PhysicalNode"]] = relationship(
        back_populates="environment", cascade="all, delete-orphan"
    )
    services: Mapped[list["SystemService"]] = relationship(
        back_populates="environment", cascade="all, delete-orphan"
    )
    clusters: Mapped[list["Cluster"]] = relationship(
        back_populates="environment", cascade="all, delete-orphan"
    )


class PhysicalNode(Base):
    __tablename__ = "physical_nodes"
    __table_args__ = (UniqueConstraint("environment_id", "hostname", name="uq_env_hostname"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    environment_id: Mapped[int] = mapped_column(ForeignKey("environments.id"), nullable=False)
    hostname: Mapped[str] = mapped_column(String(128), nullable=False)
    ip: Mapped[str] = mapped_column(String(64), nullable=False)
    os_flavor: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    environment: Mapped[Environment] = relationship(back_populates="nodes")


class SystemService(Base):
    __tablename__ = "system_services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    environment_id: Mapped[int] = mapped_column(ForeignKey("environments.id"), nullable=False)
    node_id: Mapped[int | None] = mapped_column(ForeignKey("physical_nodes.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    environment: Mapped[Environment] = relationship(back_populates="services")


class Cluster(Base):
    __tablename__ = "clusters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    environment_id: Mapped[int] = mapped_column(ForeignKey("environments.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    api_endpoint: Mapped[str] = mapped_column(String(256), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    environment: Mapped[Environment] = relationship(back_populates="clusters")
    namespaces: Mapped[list["Namespace"]] = relationship(
        back_populates="cluster", cascade="all, delete-orphan"
    )


class Namespace(Base):
    __tablename__ = "namespaces"
    __table_args__ = (UniqueConstraint("cluster_id", "name", name="uq_cluster_ns"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cluster_id: Mapped[int] = mapped_column(ForeignKey("clusters.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)

    cluster: Mapped[Cluster] = relationship(back_populates="namespaces")
    pods: Mapped[list["Pod"]] = relationship(
        back_populates="namespace", cascade="all, delete-orphan"
    )


class Pod(Base):
    __tablename__ = "pods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    namespace_id: Mapped[int] = mapped_column(ForeignKey("namespaces.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    labels: Mapped[str | None] = mapped_column(String(1024), nullable=True)  # JSON

    namespace: Mapped[Namespace] = relationship(back_populates="pods")


class CheckItem(Base):
    __tablename__ = "check_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)  # physical|service|cluster|pod
    os_flavor: Mapped[str | None] = mapped_column(String(32), nullable=True)  # None = all
    description: Mapped[str] = mapped_column(String(512), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[str] = mapped_column(String(2048), default="{}")  # JSON thresholds


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trigger: Mapped[str] = mapped_column(String(32), nullable=False)  # scheduled|manual
    triggered_by: Mapped[str] = mapped_column(String(128), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="running")  # running|finished|failed


class CheckResult(Base):
    __tablename__ = "check_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), nullable=False)
    check_item_id: Mapped[int] = mapped_column(ForeignKey("check_items.id"), nullable=False)
    object_type: Mapped[str] = mapped_column(String(32), nullable=False)
    object_name: Mapped[str] = mapped_column(String(256), nullable=False)
    environment_id: Mapped[int] = mapped_column(ForeignKey("environments.id"), nullable=False)
    os_flavor: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # normal|abnormal|unreachable|failed
    evidence: Mapped[str] = mapped_column(String(4096), default="")
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), nullable=False)
    rendered_by: Mapped[str] = mapped_column(String(128), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    html_path: Mapped[str] = mapped_column(String(512), default="")
    md_path: Mapped[str] = mapped_column(String(512), default="")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    target_ref: Mapped[str | None] = mapped_column(String(256), nullable=True)
    detail: Mapped[str] = mapped_column(String(1024), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class AppSetting(Base):
    """Key-value application settings (e.g. auto-inspection schedule)."""
    __tablename__ = "app_settings"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(512), default="")


class Finding(Base):
    """A triage record for a logical anomaly (check item x object x env).

    state: pending | resolved | ignored. Persists across runs, so once handled

    the anomaly stays marked resolved/ignored until reopened."""
    __tablename__ = "findings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    check_item_id: Mapped[int] = mapped_column(Integer, nullable=False)
    object_type: Mapped[str] = mapped_column(String(32), nullable=False)
    object_name: Mapped[str] = mapped_column(String(256), nullable=False)
    environment_id: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(16), default="pending")  # pending|resolved|ignored
    note: Mapped[str] = mapped_column(String(1024), default="")
    updated_by: Mapped[str] = mapped_column(String(128), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)
    __table_args__ = (
        UniqueConstraint(
            "check_item_id", "object_type", "object_name", "environment_id",
            name="uq_finding",
        ),
    )
