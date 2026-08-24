"""Operational models: reports, audit trail, app settings (CONTRACT §3)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.base import UTCDateTime, utcnow


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), nullable=False)
    rendered_by: Mapped[str] = mapped_column(String(128), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    html_path: Mapped[str] = mapped_column(String(512), default="")
    md_path: Mapped[str] = mapped_column(String(512), default="")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    target_ref: Mapped[str | None] = mapped_column(String(256), nullable=True)
    detail: Mapped[str] = mapped_column(String(1024), default="")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class AppSetting(Base):
    """Key-value application settings (e.g. auto-inspection schedule)."""
    __tablename__ = "app_settings"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(512), default="")
