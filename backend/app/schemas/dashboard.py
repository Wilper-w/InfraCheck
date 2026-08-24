"""Dashboard aggregate schemas (CONTRACT §4 /dashboard)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


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

    date: str  # 该次巡检 started_at，UTC "YYYY-MM-DD HH:mm"（每次巡检一个点）
    normal: int = 0
    abnormal: int = 0
    unreachable: int = 0
    failed: int = 0


class TrendResponse(BaseModel):
    series: list[TrendPoint]
