"""Deterministic dryrun transport — no network, local/demo use (CONTRACT §6)."""
from __future__ import annotations

import hashlib
import json

from app.engine.status import (
    STATUS_ABNORMAL,
    STATUS_FAILED,
    STATUS_NORMAL,
    STATUS_UNREACHABLE,
)
from app.engine.targets import TargetObject
from app.models import CheckItem
from app.runner.base import BaseRunner


class DryRunRunner(BaseRunner):
    """Deterministic dryrun transport. Produces results covering all four states
    (CONTRACT §6: '尽量让结果覆盖 normal/abnormal/unreachable/failed 四态').

    Determinism key: a stable hash of (check_item.id, object_name) so the same
    input always yields the same status, and the four states are spread across
    the seeded objects.
    """

    _STATES = (STATUS_NORMAL, STATUS_ABNORMAL, STATUS_UNREACHABLE, STATUS_FAILED)

    async def execute(self, check_item: CheckItem, target: TargetObject) -> tuple[str, str]:
        key = f"{check_item.id}|{target.object_name}"
        digest = hashlib.sha256(key.encode()).hexdigest()
        idx = int(digest[:8], 16) % 4
        status = self._STATES[idx]
        evidence = self._build_evidence(check_item, target, status, digest)
        return status, evidence

    def _build_evidence(
        self, check_item: CheckItem, target: TargetObject, status: str, digest: str
    ) -> str:
        flavor = target.os_flavor or "all"
        if status == STATUS_NORMAL:
            return json.dumps(
                {
                    "check": check_item.name,
                    "object": target.object_name,
                    "os_flavor": flavor,
                    "transport": "dryrun",
                    "verdict": "pass",
                    "detail": "all thresholds within bounds",
                },
                ensure_ascii=False,
            )
        if status == STATUS_ABNORMAL:
            return json.dumps(
                {
                    "check": check_item.name,
                    "object": target.object_name,
                    "os_flavor": flavor,
                    "transport": "dryrun",
                    "verdict": "threshold_exceeded",
                    "detail": "disk usage 92% > 85% threshold",
                },
                ensure_ascii=False,
            )
        if status == STATUS_UNREACHABLE:
            return json.dumps(
                {
                    "check": check_item.name,
                    "object": target.object_name,
                    "os_flavor": flavor,
                    "transport": "dryrun",
                    "verdict": "host_unreachable",
                    "detail": "Connection timed out (dryrun simulation)",
                },
                ensure_ascii=False,
            )
        # failed
        return json.dumps(
            {
                "check": check_item.name,
                "object": target.object_name,
                "os_flavor": flavor,
                "transport": "dryrun",
                "verdict": "check_command_error",
                "detail": f"command exited non-zero (dryrun, ref={digest[:8]})",
            },
            ensure_ascii=False,
        )
