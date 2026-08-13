"""Pydantic v2 schemas for request/response bodies (CONTRACT §4).

Grouped by domain — `common` (auth/pagination), `inventory`, `checks`,
`dashboard`, `ops` — and re-exported here so callers keep using
`from app.schemas import X`.
"""
from __future__ import annotations

from app.schemas.checks import (
    CheckItemBase,
    CheckItemCreate,
    CheckItemOut,
    CheckItemUpdate,
    CheckResultOut,
    RunDetail,
    RunOut,
    TriggerRequest,
    TriggerResponse,
)
from app.schemas.common import (
    LoginRequest,
    LoginResponse,
    MeResponse,
    Page,
    Paginated,
)
from app.schemas.dashboard import (
    DashboardSummary,
    EnvSummaryItem,
    TopIssueItem,
    TrendPoint,
    TrendResponse,
)
from app.schemas.inventory import (
    ClusterBase,
    ClusterCreate,
    ClusterOut,
    EnvironmentBase,
    EnvironmentCreate,
    EnvironmentOut,
    EnvironmentSummary,
    EnvironmentUpdate,
    NamespaceBase,
    NamespaceCreate,
    NamespaceOut,
    NodeBase,
    NodeCreate,
    NodeOut,
    PodBase,
    PodCreate,
    PodOut,
    ServiceBase,
    ServiceCreate,
    ServiceOut,
    ServiceUpdate,
)
from app.schemas.ops import AuditLogOut, ReportOut

__all__ = [
    # common
    "LoginRequest",
    "LoginResponse",
    "MeResponse",
    "Page",
    "Paginated",
    # inventory
    "EnvironmentBase",
    "EnvironmentCreate",
    "EnvironmentUpdate",
    "EnvironmentOut",
    "EnvironmentSummary",
    "NodeBase",
    "NodeCreate",
    "NodeOut",
    "ServiceBase",
    "ServiceCreate",
    "ServiceUpdate",
    "ServiceOut",
    "ClusterBase",
    "ClusterCreate",
    "ClusterOut",
    "NamespaceBase",
    "NamespaceCreate",
    "NamespaceOut",
    "PodBase",
    "PodCreate",
    "PodOut",
    # checks
    "CheckItemBase",
    "CheckItemCreate",
    "CheckItemUpdate",
    "CheckItemOut",
    "TriggerRequest",
    "TriggerResponse",
    "RunOut",
    "RunDetail",
    "CheckResultOut",
    # dashboard
    "EnvSummaryItem",
    "TopIssueItem",
    "DashboardSummary",
    "TrendPoint",
    "TrendResponse",
    # ops
    "ReportOut",
    "AuditLogOut",
]
