"""Asset inventory models: environments down to pods (CONTRACT §3)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.base import UTCDateTime, utcnow


class Environment(Base):
    __tablename__ = "environments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    os_flavor: Mapped[str] = mapped_column(String(32), nullable=False)  # ubuntu|centos
    description: Mapped[str] = mapped_column(String(512), default="")
    # Per-environment SSH chain reachable from the jump host (multi-hop):
    #   jump -> entry(host:port:user) -> [ssh root@ssh_master_ip] -> node
    # lf is one hop (entry IS master: ssh_master_ip = its internal IP for attribution);
    # hb/sh/sg/zw are two hops (entry + master via m1/ms1 target).
    ssh_entry_host: Mapped[str] = mapped_column(String(256), default="")
    ssh_entry_port: Mapped[int] = mapped_column(Integer, default=22)
    ssh_entry_user: Mapped[str] = mapped_column(String(64), default="")
    ssh_master_ip: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

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
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    environment: Mapped[Environment] = relationship(back_populates="nodes")


class SystemService(Base):
    __tablename__ = "system_services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    environment_id: Mapped[int] = mapped_column(ForeignKey("environments.id"), nullable=False)
    node_id: Mapped[int | None] = mapped_column(ForeignKey("physical_nodes.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # 探测方式：systemd（默认）| port（监听端口）| vip（虚拟 IP 绑定）
    probe_mode: Mapped[str] = mapped_column(String(16), default="systemd", nullable=False)
    # vip 模式存虚拟 IP；systemd/port 模式留空则回落到 name/port
    probe_target: Mapped[str | None] = mapped_column(String(128), nullable=True)

    environment: Mapped[Environment] = relationship(back_populates="services")


class Cluster(Base):
    __tablename__ = "clusters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    environment_id: Mapped[int] = mapped_column(ForeignKey("environments.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    api_endpoint: Mapped[str] = mapped_column(String(256), default="")
    exec_host: Mapped[str] = mapped_column(String(256), default="")  # SSH/kubectl host for checks
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

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
