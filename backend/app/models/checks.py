"""Inspection models: check items, runs, results, findings (CONTRACT §3)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.base import UTCDateTime, utcnow


class CheckItem(Base):
    __tablename__ = "check_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)  # physical|service|cluster|pod
    os_flavor: Mapped[str | None] = mapped_column(String(32), nullable=True)  # None = all
    description: Mapped[str] = mapped_column(String(512), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[str] = mapped_column(String(2048), default="{}")  # JSON thresholds


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trigger: Mapped[str] = mapped_column(String(32), nullable=False)  # scheduled|manual
    triggered_by: Mapped[str] = mapped_column(String(128), nullable=False)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="running")  # running|finished|failed
    # 逐环境增量巡检的进度说明（如「已完成 1/2 个环境 · 累计 N 条」）
    progress_note: Mapped[str | None] = mapped_column(String(256), nullable=True)


class CheckResult(Base):
    __tablename__ = "check_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), nullable=False)
    check_item_id: Mapped[int] = mapped_column(ForeignKey("check_items.id"), nullable=False)
    object_type: Mapped[str] = mapped_column(String(32), nullable=False)
    object_name: Mapped[str] = mapped_column(String(256), nullable=False)
    environment_id: Mapped[int] = mapped_column(ForeignKey("environments.id"), nullable=False)
    os_flavor: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # normal|abnormal|unreachable|failed
    evidence: Mapped[str] = mapped_column(String(4096), default="")
    captured_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class Finding(Base):
    """A triage record for a logical anomaly (check item x object x env).

    state: pending | resolved | ignored. Persists across runs, so once handled

    the anomaly stays marked resolved/ignored until reopened."""
    __tablename__ = "findings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    check_item_id: Mapped[int] = mapped_column(Integer, nullable=False)
    object_type: Mapped[str] = mapped_column(String(32), nullable=False)
    object_name: Mapped[str] = mapped_column(String(256), nullable=False)
    environment_id: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(16), default="pending")  # pending|resolved|ignored
    note: Mapped[str] = mapped_column(String(1024), default="")
    updated_by: Mapped[str] = mapped_column(String(128), default="")
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)
    __table_args__ = (
        UniqueConstraint(
            "check_item_id", "object_type", "object_name", "environment_id",
            name="uq_finding",
        ),
    )
