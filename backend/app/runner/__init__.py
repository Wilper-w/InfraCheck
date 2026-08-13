"""Runner transports (CONTRACT §6). dryrun default + real ssh via jump host ProxyJump.

- dryrun: deterministic, covers all four result states for local/demo use.
- ssh: real execution via asyncssh, connecting to the jump host and then
  opening a nested SSH connection through it (connect_ssh == ProxyJump) to the
  target, running an OS-dispatched command, and mapping exit status to a result.
"""
from __future__ import annotations

import asyncio
import hashlib
import json

from app.engine import (
    STATUS_ABNORMAL,
    STATUS_FAILED,
    STATUS_NORMAL,
    STATUS_UNREACHABLE,
    TargetObject,
)
from app.models import CheckItem


class BaseRunner:
    """Interface: execute a check item against one target object."""

    async def execute(self, check_item: CheckItem, target: TargetObject) -> tuple[str, str]:
        raise NotImplementedError


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


def _command_for(check_item: CheckItem, target: TargetObject) -> str:
    """Dispatched shell command per target_type (OS-differentiated where it matters).

    exit 0 => normal; non-zero => abnormal; connect/run failure => unreachable/failed.
    systemd vs init: keepalived/haproxy may run under init on legacy boxes; for
    these five environments systemd is assumed (Ubuntu 22/24 & CentOS 8 all ship
    systemd), so `systemctl is-active` is used uniformly.
    """
    tt = target.object_type
    if tt == "service":
        name = target.object_name.split("@")[0]
        return f"systemctl is-active {name}"
    if tt == "physical":
        return "hostname && uptime"
    # cluster/pod checks run against the k8s API via a control-plane host; the
    # MVP transport executes a lightweight probe command to prove connectivity.
    return "true"


class SshRunner(BaseRunner):
    """Real SSH transport via jump host + nested SSH (asyncssh `connect_ssh`,
    i.e. ProxyJump). Requires JUMP_HOST/JUMP_USER/(key) and a target `address`.
    Without a configured jump host or a resolvable address it returns
    `unreachable` with an explicit reason — no silent stub.
    """

    async def execute(self, check_item: CheckItem, target: TargetObject) -> tuple[str, str]:
        from app import config

        if not config.JUMP_HOST:
            return (STATUS_UNREACHABLE, self._evidence(check_item, target, "no_jump_host_configured", "JUMP_HOST not set"))
        if not target.address:
            return (STATUS_UNREACHABLE, self._evidence(check_item, target, "no_target_address", "target has no SSH address embedded in inventory"))

        cmd = _command_for(check_item, target)
        try:
            return await asyncio.wait_for(
                self._run_via_jump(check_item, target, cmd),
                timeout=config.SSH_TIMEOUT,
            )
        except asyncio.TimeoutError:
            return (STATUS_UNREACHABLE, self._evidence(check_item, target, "connection_timeout", f"timed out after {config.SSH_TIMEOUT}s"))
        except Exception as exc:  # connect/auth/run failures => unreachable
            return (STATUS_UNREACHABLE, self._evidence(check_item, target, "connection_failed", str(exc)[:300]))

    async def _run_via_jump(
        self, check_item: CheckItem, target: TargetObject, cmd: str
    ) -> tuple[str, str]:
        from app import config

        import asyncssh

        base = dict(known_hosts=None, client_keys=(config.JUMP_KEY or None))
        jump = await asyncssh.connect(
            config.JUMP_HOST, port=config.SSH_PORT, username=config.JUMP_USER or "root", **base
        )
        try:
            tconn = await jump.connect_ssh(
                target.address,
                port=config.SSH_PORT,
                username=config.SSH_USER or "root",
                **base,
            )
            try:
                proc = await tconn.run(cmd)
                output = (proc.stdout or "") + (proc.stderr or "")
                return self._classify(check_item, target, proc.exit_status, output)
            finally:
                tconn.close()
                await tconn.wait_closed()
        finally:
            jump.close()
            await jump.wait_closed()

    @staticmethod
    def _classify(
        check_item: CheckItem, target: TargetObject, exit_code: int, output: str
    ) -> tuple[str, str]:
        """Map a real remote command's exit status to a result state.

        exit 0 => normal; non-zero => abnormal (the check ran and failed).
        (Connection/auth/timeout failures never reach here — they are handled in
        `execute` and mapped to unreachable.)
        """
        detail = output.strip()[:300] or f"(empty output, exit={exit_code})"
        if exit_code == 0:
            return STATUS_NORMAL, SshRunner._evidence(check_item, target, "pass", detail, output)
        return STATUS_ABNORMAL, SshRunner._evidence(check_item, target, "command_nonzero", detail, output)

    @staticmethod
    def _evidence(check_item: CheckItem, target: TargetObject, verdict: str, detail: str, output: str = "") -> str:
        return json.dumps(
            {
                "check": check_item.name,
                "object": target.object_name,
                "address": target.address,
                "os_flavor": target.os_flavor or "all",
                "transport": "ssh",
                "verdict": verdict,
                "detail": detail,
                "output": output,
            },
            ensure_ascii=False,
        )


def get_runner(transport: str) -> BaseRunner:
    if transport == "ssh":
        return SshRunner()
    return DryRunRunner()
