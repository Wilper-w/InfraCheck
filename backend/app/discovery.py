"""K8s node auto-discovery: import nodes from `kubectl get nodes -o wide`.

Reaches the environment's k8s control-plane (SSH_GATEWAY -> gateway node, where
kubectl runs) through the jump host, parses node NAME / INTERNAL-IP / OS-IMAGE,
and maps OS to a platform flavor. Pure parsing is unit-testable; the SSH hop is
kept as a thin shell-out so the same mechanism as live checks is used.
"""
from __future__ import annotations

import os
import re
import subprocess

from app import config

_KERNEL_RE = re.compile(r"^\d+\.\d+")


def os_flavor_from(image: str) -> str:
    """Map a k8s OS-IMAGE to a platform os_flavor.

    YDLinux / AliYun / Anolis / RHEL-family are treated as RHEL-ish 'centos'
    (they ship systemd + coreutils, so the same resource/service checks apply).
    """
    low = (image or "").lower()
    if "ubuntu" in low or "debian" in low:
        return "ubuntu"
    # everything RHEL-family (centos/rocky/anolis/yunalinux/alinux/red hat/...) -> centos
    return "centos"


def parse_nodes_output(text: str) -> list[dict]:
    """Parse `kubectl get nodes -o wide` output into node dicts."""
    nodes: list[dict] = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 7:
            continue
        name = parts[0]
        if name in ("NAME",) or not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9\-.]+$", name):
            continue
        status = parts[1]
        internal_ip = parts[5]
        if internal_ip in ("<none>", "INTERNAL-IP"):
            continue
        # OS-IMAGE follows INTERNAL-IP & EXTERNAL-IP; kernel column starts a digit-dot token
        os_tokens = []
        for t in parts[7:]:
            if _KERNEL_RE.match(t):
                break
            os_tokens.append(t)
        nodes.append(
            {
                "hostname": name,
                "ip": internal_ip,
                "status": status,
                "os_image": " ".join(os_tokens),
            }
        )
    return nodes


def _local_ssh_base() -> list[str]:
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20"]
    if config.JUMP_KEY:
        cmd += ["-i", os.path.expanduser(config.JUMP_KEY)]
    cmd += [f"{config.JUMP_USER or 'root'}@{config.JUMP_HOST}"]
    return cmd


def _run_on_gateway(gateway_argv: list[str], timeout: int = 90) -> str:
    """Run a command on the gateway node, reached via the jump host."""
    # build the ssh-to-gateway as a single remote command for the jump shell
    gw_user = config.SSH_GATEWAY_USER or "root"
    inner = " ".join(gateway_argv)
    # pass through the jump host: ssh jump 'ssh -p GW_PORT <user>@GW <inner>'
    hop = f"ssh -o BatchMode=yes -o ConnectTimeout=20 -p {config.SSH_GATEWAY_PORT} {gw_user}@{config.SSH_GATEWAY} '{inner.replace(chr(39), chr(39)+chr(92)+chr(39)+chr(39))}'"
    r = subprocess.run(_local_ssh_base() + [hop], capture_output=True, text=True, timeout=timeout)
    return (r.stdout or "").strip() or (r.stderr or "").strip()


def discover_k8s_nodes(chain: dict | None = None) -> list[dict]:
    """Query the environment's cluster and return discovered nodes (no import).

    `chain` is a per-environment SSH chain (entry + optional master hop); when
    omitted the legacy global gateway config is used.
    """
    from app import collector
    _rc, raw = collector.run_on_master("kubectl get nodes -o wide --no-headers", chain=chain, timeout=90)
    return parse_nodes_output(raw)
