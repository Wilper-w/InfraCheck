"""The four inspection result states (CONTRACT §6).

Kept in its own module so runners can import the states without pulling in the
executor, which imports the runners back.
"""
from __future__ import annotations

STATUS_NORMAL = "normal"
STATUS_ABNORMAL = "abnormal"
STATUS_UNREACHABLE = "unreachable"
STATUS_FAILED = "failed"

ALL_STATUSES = (STATUS_NORMAL, STATUS_ABNORMAL, STATUS_UNREACHABLE, STATUS_FAILED)
