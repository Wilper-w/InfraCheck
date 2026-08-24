"""Real SSH transport via jump host ProxyJump (CONTRACT §6)."""
from __future__ import annotations

import asyncio
import json

from app.engine.status import STATUS_ABNORMAL, STATUS_NORMAL, STATUS_UNREACHABLE
from app.engine.targets import TargetObject
from app.models import CheckItem
from app.runner.base import BaseRunner
from app.runner import safety
from app import checks as check_builders
from app.engine import parse_config


def _command_for(check_item: CheckItem, target: TargetObject) -> str:
    """Dispatched shell command per target_type (OS-differentiated where it matters).

    - physical: resource threshold script (CPU/mem/disk/load).
    - service:  probe_mode dispatch (systemd/port/vip); systemd gets a service health probe.
    - cluster:  kubectl node/pod health on the control-plane host (exec_host).
    - pod:      kubectl pod phase/ready/restart on the control-plane host.
    exit 0 => normal; non-zero => abnormal; connect/run failure => unreachable.
    """
    tt = target.object_type
    if tt == "physical":
        return check_builders.resource_script(parse_config(check_item), target.os_flavor or "unknown")
    if tt == "cluster":
        return check_builders.cluster_script(parse_config(check_item))
    if tt == "pod":
        ns, _, pod = target.object_name.partition("/")
        return check_builders.pod_script(ns, pod)
    if tt == "service":
        name = target.object_name.split("@")[0]
        mode = target.probe_mode or "systemd"
        if mode == "port" and target.probe_port:
            return f"ss -ltnH 'sport = :{target.probe_port}' | grep -q LISTEN"
        if mode == "vip" and target.probe_target:
            return f"ip -o addr show | grep -qw {target.probe_target}"
        return check_builders.service_script(name, parse_config(check_item), target.os_flavor or "unknown")
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
        reason = safety.blocked_reason(cmd)
        if reason:
            return (STATUS_ABNORMAL, self._evidence(check_item, target, "safety_blocked", f"blocked destructive operation: {reason}", cmd))
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

        base = dict(known_hosts=(config.KNOWN_HOSTS or None), client_keys=(config.JUMP_KEY or None))
        jump = await asyncssh.connect(
            config.JUMP_HOST, port=config.SSH_PORT, username=config.JUMP_USER or "root", **base
        )
        try:
            if getattr(config, "SSH_VIA_JUMP_SHELL", False):
                # Alias mode: run the node-check command ON the jump host, reusing its
                # own ssh aliases/keys/agent. SSH_NODE_COMMAND is the executable that
                # reaches a node — default `ssh <address>`, or your own wrapper such as
                # `lf` (which itself already invokes ssh). `{address}` is replaced by
                # the target's inventory address when present.
                # Build the command that reaches the target node from the jump host.
                # Two shapes:
                #  - gateway:  jump -> SSH_GATEWAY:<port> -> `ssh root@{address} '<cmd>'`
                #              (double-escaping so multi-line cmds with quotes survive)
                #  - direct:   jump -> SSH_NODE_COMMAND (default `ssh {address}`) + '<cmd>'
                node_cmd = (config.SSH_NODE_COMMAND or "").strip()
                if not node_cmd:
                    node_cmd = "ssh -o BatchMode=yes {address}"
                escaped = cmd.replace("'", "'\\''")
                if getattr(config, "SSH_GATEWAY", ""):
                    inner = ("ssh -o BatchMode=yes root@{address} '" + escaped + "'").replace("{address}", target.address or "")
                    # escape the whole inner line so it survives JUMP's shell single-quoting
                    outer = ("ssh -o BatchMode=yes -p " + str(config.SSH_GATEWAY_PORT)
                             + " root@" + config.SSH_GATEWAY + " '"
                             + inner.replace("'", "'\\''") + "'")
                    shell_cmd = outer
                else:
                    hop = node_cmd.replace("{address}", target.address or "")
                    shell_cmd = hop + " '" + escaped + "'"
                # source common rc files so shell functions/aliases are defined
                proc = await jump.run("source ~/.bashrc 2>/dev/null; " + shell_cmd)
                output = ((proc.stdout or "") + (proc.stderr or "")).strip()
                return self._classify(check_item, target, proc.exit_status, output)
            # Default mode: nested SSH jump->node over raw protocol (platform key on node).
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
