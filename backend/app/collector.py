"""Ansible & single-master execution helpers, per-environment chain aware.

Chain model (reachable from the jump host):
    jump -> entry(host:port:user) -> [ssh root@master_ip] -> node
  - entry: a jump-reachable host/port/user into an environment.
  - master_ip: (optional) the environment's master internal IP reachable from the
    entry; DB/etcd checks and ansible fan-out run there. Empty => run on entry
    directly (the one-hop "lf" shape).

Every function accepts `chain` (dict with host/port/user/master_ip); when None it
falls back to the legacy global SSH_GATEWAY* config, so existing deployments do
not regress.
"""
from __future__ import annotations

import base64
import os
import re
import subprocess

from app import config

_LINE_RE = re.compile(
    r"^(?P<ip>\S+)\s*\|\s*(?P<state>CHANGED|FAILED|UNREACHABLE|OK|SUCCESS)"
    r"(?:!\s*|\s+)(?P<body>.*)$",
    re.DOTALL,
)


def ansible_dir() -> str:
    return os.getenv("SSH_ANSIBLE_DIR", "/nvme/infracheck_ansible")


def resolve_chain(chain: dict | None) -> dict:
    """Normalize a chain dict, falling back to legacy global config."""
    if not chain:
        chain = {}
    return {
        "host": chain.get("host") or config.SSH_GATEWAY or "",
        "port": int(chain.get("port") or config.SSH_GATEWAY_PORT or "22"),
        "user": chain.get("user") or config.SSH_GATEWAY_USER or "root",
        "master_ip": chain.get("master_ip") or "",
    }


def _local_ssh_base() -> list[str]:
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20"]
    if config.JUMP_KEY:
        cmd += ["-i", os.path.expanduser(config.JUMP_KEY)]
    cmd += [f"{config.JUMP_USER or 'root'}@{config.JUMP_HOST}"]
    return cmd


def _ssh(host: str, port: int, user: str, remote_cmd: str) -> str:
    esc = remote_cmd.replace(chr(39), chr(39) + chr(92) + chr(39) + chr(39))
    return (
        f"ssh -o BatchMode=yes -o ConnectTimeout=20 -p {port} {user}@{host} '{esc}'"
    )


def _run(gateway_hop: str, timeout: int) -> str:
    r = subprocess.run(_local_ssh_base() + [gateway_hop], capture_output=True, text=True, timeout=timeout)
    return (r.stdout or "").strip() or (r.stderr or "").strip()


def _gateway(command: str, chain: dict | None = None, timeout: int = 300) -> str:
    """Run `command` on the environment's entry node (one hop from jump)."""
    c = resolve_chain(chain)
    return _run(_ssh(c["host"], c["port"], c["user"], command), timeout)



def _master_shell(script: str, chain: dict | None, timeout: int) -> str:
    """Return a command that runs `script` on the env's master (entry -> master)."""
    c = resolve_chain(chain)
    b64 = base64.b64encode(script.encode()).decode()
    run = f"echo {b64} | base64 -d > /tmp/ic_single.sh && timeout {timeout} bash /tmp/ic_single.sh; echo __IC_RC__=$?"
    if c["master_ip"]:
        # two-hop: hop through the entry to the master, then run the script there
        return _ssh(c["host"], c["port"], c["user"], _ssh(c["master_ip"], 22, "root", run))
    return _ssh(c["host"], c["port"], c["user"], run)


def run_on_master(script: str, chain: dict | None = None, timeout: int = 120) -> tuple[int, str]:
    """Run a check script on the env's master directly (no ansible)."""
    hop = _master_shell(script, chain, timeout)
    out = _run(hop, timeout + 30)
    rc = 0
    m = re.search(r"__IC_RC__=(\d+)", out)
    if m:
        rc = int(m.group(1))
        out = out.replace(m.group(0), "")
    return rc, (out or "").strip()


def gateway_internal_ip(chain: dict | None = None, timeout: int = 30) -> str:
    """The env master internal IP (result attribution). Uses master_ip if set,
    else the entry's own IP."""
    c = resolve_chain(chain)
    if c["master_ip"]:
        return c["master_ip"]
    out = _gateway("hostname -I 2>/dev/null | awk '{print $1}'", chain, timeout)
    return out.split()[0] if out.strip() else ""


def sync_inventory(node_ips: list[str], chain: dict | None = None) -> None:
    hosts = "\n".join(node_ips) + "\n"
    b64 = base64.b64encode(hosts.encode()).decode()
    cmd = (
        f"mkdir -p {ansible_dir()} && echo {b64} | base64 -d > {ansible_dir()}/hosts && "
        f"echo WROTE && wc -l < {ansible_dir()}/hosts"
    )
    _gateway(cmd, chain)


def run_ansible(script: str, chain: dict | None = None, timeout: int = 300) -> str:
    """Run a read-only shell script over the inventory via ansible on the env's
    MASTER (reachable through the entry when master_ip is set)."""
    b64 = base64.b64encode(script.encode()).decode()
    run = (
        f"mkdir -p {ansible_dir()} && echo {b64} | base64 -d > {ansible_dir()}/.check.sh && "
        f"cd {ansible_dir()} && timeout {timeout} ansible all -m script -a /nvme/infracheck_ansible/.check.sh --one-line 2>/dev/null"
    )
    c = resolve_chain(chain)
    if c["master_ip"]:
        hop = _ssh(c["host"], c["port"], c["user"], _ssh(c["master_ip"], 22, "root", run))
    else:
        hop = _ssh(c["host"], c["port"], c["user"], run)
    return _run(hop, timeout + 30)


def parse_results(raw: str) -> list[dict]:
    results: list[dict] = []
    for line in raw.splitlines():
        m = _LINE_RE.match(line)
        if not m:
            continue
        ip = m.group("ip")
        state = m.group("state")
        body = m.group("body")
        rc = 1
        out = ""
        if state in ("CHANGED", "OK"):
            # script-module form:  IP | CHANGED => {"rc":0,"stdout":"...","stderr":"..."}
            jrc = re.search(r'"rc":\s*(\d+)', body)
            jout = re.search(r'"stdout":\s*"((?:[^"\\]|\\.)*)"', body, re.DOTALL)
            jerr = re.search(r'"stderr":\s*"((?:[^"\\]|\\.)*)"', body, re.DOTALL)
            if jrc:
                rc = int(jrc.group(1))
                out = (jout.group(1) if jout else "").replace("\\r", "").strip()
                if not out:
                    out = (jerr.group(1) if jerr else "").replace("\\r", "").strip()
            else:
                # old one-line form:  rc=0 | (stdout) ...
                rcm = re.search(r"rc=(\d+)", body)
                if rcm:
                    rc = int(rcm.group(1))
                om = re.search(r"\(stdout\)\s*(.*)$", body, re.DOTALL)
                if om:
                    out = (om.group(1) or "").strip()
        elif state == "FAILED":
            jm = re.search(r"rc[=:]\s*(\d+)", body)
            jmsg = re.search(r'"msg":\s*"([^"]*)"', body)
            jout = re.search(r'"stdout":\s*"([^"]*)"', body)
            jerr = re.search(r'"stderr":\s*"([^"]*)"', body)
            if jm:
                rc = int(jm.group(1))
            pieces = [jout.group(1) if jout else "", jerr.group(1) if jerr else ""]
            out = "\n".join(p for p in pieces if p)
            if not out:
                out = jmsg.group(1) if jmsg else body[:200]
        results.append({"ip": ip, "rc": rc, "state": state, "out": out})
    return results


def detect_masters(chain: dict | None = None) -> list[str]:
    """Control-plane node internal IPs from kubectl on the env's master."""
    c = resolve_chain(chain)
    if c["master_ip"]:
        kw = _ssh(c["master_ip"], 22, "root",
                  "kubectl get nodes -o wide --no-headers 2>/dev/null | awk '/control-plane/{print $6}'")
        return [t for t in _run(_ssh(c["host"], c["port"], c["user"], kw), 60).splitlines() if t and t != "<none>"]
    return [t for t in _gateway(
        "kubectl get nodes -o wide --no-headers 2>/dev/null | awk '/control-plane/{print $6}'", chain, 60
    ).splitlines() if t and t != "<none>"]
