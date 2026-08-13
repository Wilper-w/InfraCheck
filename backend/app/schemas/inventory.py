"""Asset inventory schemas: environment, node, service, cluster, namespace, pod."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ---- environment ----
class EnvironmentBase(BaseModel):
    name: str
    os_flavor: str
    description: str = ""


class EnvironmentCreate(EnvironmentBase):
    pass


class EnvironmentUpdate(BaseModel):
    name: Optional[str] = None
    os_flavor: Optional[str] = None
    description: Optional[str] = None


class EnvironmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    os_flavor: str
    description: str
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
class ServiceBase(BaseModel):
    name: str
    node_id: Optional[int] = None
    port: Optional[int] = None
    enabled: bool = True


class ServiceCreate(ServiceBase):
    pass


class ServiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    environment_id: int
    node_id: Optional[int] = None
    name: str
    port: Optional[int] = None
    enabled: bool


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
