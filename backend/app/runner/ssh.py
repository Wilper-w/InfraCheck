"""Real SSH transport via jump host ProxyJump (CONTRACT §6)."""
from __future__ import annotations

import asyncio
import json

from app.engine.status import STATUS_ABNORMAL, STATUS_NORMAL, STATUS_UNREACHABLE
from app.engine.targets import TargetObject
from app.models import CheckItem
from app.runner.base import BaseRunner


def _command_for(check_item: CheckItem, target: TargetObject) -> str:
    """Dispatched shell command per target_type (OS-differentiated where it matters).

    exit 0 => normal; non-zero => abnormal; connect/run failure => unreachable/failed.

    Services dispatch further on `probe_mode` (CONTRACT §3/§6):
    - systemd: `systemctl is-active` — standard unit-managed services.
    - port:    listening socket check — proves the service actually serves.
    - vip:     virtual-IP binding — for keepalived, a live process on the wrong
               node is still a failure; only the node holding the VIP is healthy.
    """
    tt = target.object_type
    if tt == "service":
        name = target.object_name.split("@")[0]
        mode = target.probe_mode or "systemd"
        if mode == "port" and target.probe_port:
            # -H 去表头，有监听行则 grep 退出 0
            return f"ss -ltnH 'sport = :{target.probe_port}' | grep -q LISTEN"
        if mode == "vip" and target.probe_target:
            return f"ip -o addr show | grep -qw {target.probe_target}"
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
