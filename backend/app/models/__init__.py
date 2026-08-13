"""SQLAlchemy ORM models (CONTRACT §3).

Models are grouped by domain — `inventory` (assets), `checks` (inspection),
`ops` (reports/audit/settings) — and re-exported here, so callers keep using
`from app.models import X`. Importing this package registers every table on
`Base.metadata`, which `create_all()` relies on.
"""
from __future__ import annotations

from app.models.base import utcnow
from app.models.checks import CheckItem, CheckResult, Finding, Run
from app.models.inventory import (
    Cluster,
    Environment,
    Namespace,
    PhysicalNode,
    Pod,
    SystemService,
)
from app.models.ops import AppSetting, AuditLog, Report

__all__ = [
    "utcnow",
    # inventory
    "Environment",
    "PhysicalNode",
    "SystemService",
    "Cluster",
    "Namespace",
    "Pod",
    # checks
    "CheckItem",
    "Run",
    "CheckResult",
    "Finding",
    # ops
    "Report",
    "AuditLog",
    "AppSetting",
]
