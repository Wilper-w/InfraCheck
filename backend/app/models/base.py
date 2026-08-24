"""Shared helpers for the ORM models."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime as _SA_DateTime
from sqlalchemy.types import TypeDecorator


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """DateTime that stores UTC and re-attaches tzinfo on read.

    SQLite drops tzinfo (values come back naive); this treats them as UTC so the
    API serializes them with `+00:00`, letting clients render correct local time.
    """

    impl = _SA_DateTime
    cache_ok = True

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
