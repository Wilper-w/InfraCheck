"""Runner transport interface (CONTRACT §6)."""
from __future__ import annotations

from app.engine.targets import TargetObject
from app.models import CheckItem


class BaseRunner:
    """Interface: execute a check item against one target object."""

    async def execute(self, check_item: CheckItem, target: TargetObject) -> tuple[str, str]:
        raise NotImplementedError
