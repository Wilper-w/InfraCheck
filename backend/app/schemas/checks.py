"""Inspection schemas: check items, run trigger/detail, check results."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


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
    progress_note: Optional[str] = None


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
