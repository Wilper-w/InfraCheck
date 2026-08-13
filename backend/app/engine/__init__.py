"""Inspection execution engine (CONTRACT §6).

Resolves check-item target objects, dispatches commands per os_flavor, and
produces CheckResult rows. The runner transport (dryrun|ssh) is selected via
RUNNER_TRANSPORT.

Split into `status` (result states), `targets` (what to inspect) and
`executor` (running it); everything is re-exported here so callers keep using
`from app.engine import X`.
"""
from __future__ import annotations

from app.engine.executor import execute_run, parse_config, select_check_items
from app.engine.status import (
    ALL_STATUSES,
    STATUS_ABNORMAL,
    STATUS_FAILED,
    STATUS_NORMAL,
    STATUS_UNREACHABLE,
)
from app.engine.targets import TargetObject, matches_flavor, resolve_targets

__all__ = [
    "STATUS_NORMAL",
    "STATUS_ABNORMAL",
    "STATUS_UNREACHABLE",
    "STATUS_FAILED",
    "ALL_STATUSES",
    "TargetObject",
    "resolve_targets",
    "matches_flavor",
    "select_check_items",
    "execute_run",
    "parse_config",
]
