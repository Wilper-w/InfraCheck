"""Pydantic v2 schemas for request/response bodies (CONTRACT §4)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---- auth ----
class LoginRequest(BaseModel):
    account: str


class LoginResponse(BaseModel):
    token: str
    account: str


class MeResponse(BaseModel):
    account: str


# ---- pagination ----
class Page(BaseModel):
    page: int = 1
    page_size: int = 20


class Paginated(BaseModel):
    items: list[Any]
    total: int
    page: int
    page_size: int


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


# ---- check item ----
class CheckItemBase(BaseModel):
    name: str
    target_type: str
    os_flavor: Optional[str] = None
    description: str = ""
    config: str = "{}"


class CheckItemCreate(CheckItemBase):
    pass


class CheckItemUpdate(BaseModel):
    name: Optional[str] = None
    target_type: Optional[str] = None
    os_flavor: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    config: Optional[str] = None


class CheckItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    target_type: str
    os_flavor: Optional[str] = None
    description: str
    enabled: bool
    config: str


# ---- run ----
class TriggerRequest(BaseModel):
    scope: str = "all"  # all|environment|check
    environment_id: Optional[int] = None
    check_item_id: Optional[int] = None


class TriggerResponse(BaseModel):
    run_id: int


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    trigger: str
    triggered_by: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    status: str


class RunDetail(RunOut):
    results: dict[str, int] = Field(default_factory=dict)


# ---- result ----
class CheckResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    run_id: int
    check_item_id: int
    object_type: str
    object_name: str
    environment_id: int
    os_flavor: Optional[str] = None
    status: str
    evidence: str
    captured_at: datetime


# ---- dashboard ----
class EnvSummaryItem(BaseModel):
    environment_id: int
    name: str
    os_flavor: str = ""
    normal: int = 0
    abnormal: int = 0
    unreachable: int = 0
    failed: int = 0
    total: int = 0


class TopIssueItem(BaseModel):
    check_item_id: int = 0
    object_type: str
    object_name: str
    environment_id: int
    environment_name: str
    status: str
    evidence: str
    captured_at: datetime
    state: str = "pending"  # pending | resolved | ignored (from Finding)
    note: str = ""
    total: int = 0


class DashboardSummary(BaseModel):
    generated_at: datetime
    total: int = 0
    normal: int = 0
    abnormal: int = 0
    unreachable: int = 0
    failed: int = 0
    environments: list[EnvSummaryItem] = []


class TrendPoint(BaseModel):
    date: str  # YYYY-MM-DD
    normal: int = 0
    abnormal: int = 0
    unreachable: int = 0
    failed: int = 0


class TrendResponse(BaseModel):
    series: list[TrendPoint]


# ---- report ----
class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    run_id: int
    rendered_by: str
    generated_at: datetime
    html_path: str
    md_path: str


# ---- audit ----
class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    actor: str
    action: str
    target_ref: Optional[str] = None
    detail: str
    created_at: datetime
