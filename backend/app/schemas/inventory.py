"""Asset inventory schemas: environment, node, service, cluster, namespace, pod."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


# ---- environment ----
class EnvironmentBase(BaseModel):
    name: str
    os_flavor: str
    description: str = ""
    # per-environment SSH chain (multi-hop) reachable from the jump host
    ssh_entry_host: str = ""
    ssh_entry_port: int = 22
    ssh_entry_user: str = ""
    ssh_master_ip: str = ""


class EnvironmentCreate(EnvironmentBase):
    pass


class EnvironmentUpdate(BaseModel):
    name: Optional[str] = None
    os_flavor: Optional[str] = None
    description: Optional[str] = None
    ssh_entry_host: Optional[str] = None
    ssh_entry_port: Optional[int] = None
    ssh_entry_user: Optional[str] = None
    ssh_master_ip: Optional[str] = None


class EnvironmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    os_flavor: str
    description: str
    ssh_entry_host: str = ""
    ssh_entry_port: int = 22
    ssh_entry_user: str = ""
    ssh_master_ip: str = ""
    created_at: datetime


class EnvironmentSummary(BaseModel):
    environment_id: int
    environment_name: str
    os_flavor: str
    total: int = 0
    normal: int = 0
    abnormal: int = 0
    unreachable: int = 0
    failed: int = 0


# ---- node ----
class NodeBase(BaseModel):
    hostname: str
    ip: str
    os_flavor: Optional[str] = None


class NodeCreate(NodeBase):
    pass


class NodeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    environment_id: int
    hostname: str
    ip: str
    os_flavor: Optional[str] = None
    created_at: datetime


# ---- service ----
PROBE_MODES = ("systemd", "port", "vip")


class ServiceBase(BaseModel):
    name: str
    node_id: Optional[int] = None
    port: Optional[int] = None
    enabled: bool = True
    probe_mode: str = "systemd"
    probe_target: Optional[str] = None

    @field_validator("probe_mode")
    @classmethod
    def _valid_mode(cls, v: str) -> str:
        if v not in PROBE_MODES:
            raise ValueError(f"probe_mode must be one of {PROBE_MODES}")
        return v

    @model_validator(mode="after")
    def _mode_requires_target(self):
        """port 模式需要端口，vip 模式需要 VIP 地址，否则探测无从下手。"""
        if self.probe_mode == "port" and self.port is None:
            raise ValueError("probe_mode=port requires a port")
        if self.probe_mode == "vip" and not (self.probe_target or "").strip():
            raise ValueError("probe_mode=vip requires probe_target (the virtual IP)")
        return self


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    node_id: Optional[int] = None
    port: Optional[int] = None
    enabled: Optional[bool] = None
    probe_mode: Optional[str] = None
    probe_target: Optional[str] = None

    @field_validator("probe_mode")
    @classmethod
    def _valid_mode(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in PROBE_MODES:
            raise ValueError(f"probe_mode must be one of {PROBE_MODES}")
        return v


class ServiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    environment_id: int
    node_id: Optional[int] = None
    name: str
    port: Optional[int] = None
    enabled: bool
    probe_mode: str = "systemd"
    probe_target: Optional[str] = None


# ---- cluster / namespace / pod ----
class ClusterBase(BaseModel):
    name: str
    api_endpoint: str = ""


class ClusterCreate(ClusterBase):
    pass


class ClusterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    environment_id: int
    name: str
    api_endpoint: str
    created_at: datetime


class NamespaceBase(BaseModel):
    name: str


class NamespaceCreate(NamespaceBase):
    pass


class NamespaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    cluster_id: int
    name: str


class PodBase(BaseModel):
    name: str
    labels: Optional[str] = None


class PodCreate(PodBase):
    pass


class PodOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    namespace_id: int
    name: str
    labels: Optional[str] = None
