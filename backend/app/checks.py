"""Real check command builders (CONTRACT §6).

Dispatches per target_type + os_flavor. Returns a POSIX sh script whose exit
code is 0 on pass (normal) and non-zero on fail (abnormal); stdout is captured
as evidence. Thresholds come from check_item.config (JSON), with sensible
defaults. Reached from the jump host via ProxyJump to the target node.
"""
from __future__ import annotations

import json
import shlex

from app.engine import TargetObject
from app.models import CheckItem


def _config(check_item: CheckItem) -> dict:
    try:
        d = json.loads(check_item.config or "{}") if check_item.config else {}
        return d if isinstance(d, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _num(cfg: dict, key: str, default: int) -> int:
    # accept both `<key>` and `<key>_threshold` (seed vs later configs)
    for k in (key, key + "_threshold"):
        if k in cfg:
            try:
                return int(cfg[k])
            except (TypeError, ValueError):
                continue
    return default


def _fail(script: list[str], label: str, detail: str) -> list[str]:
    script.append(f'echo "{label}:{detail}"; exit 1')
    return script


# ---------------------------------------------------------------------------
# 物理机资源阈值检查（CPU/内存/磁盘/负载）
# ---------------------------------------------------------------------------
def resource_script(cfg: dict, os_flavor: str) -> str:
    # load_max = per-core load cap (load vs nproc); mem/disk = percent caps.
    load_max = _num(cfg, "load", 2)
    mem_max = _num(cfg, "mem", 90)           # %
    disk_max = _num(cfg, "disk", 85)         # %
    script = [
        "hostname",
        f'echo "os={os_flavor}"',
        "load=$(awk '{print $1}' /proc/loadavg 2>/dev/null)",
        "cores=$(nproc 2>/dev/null || echo 1)",
        "mem=$(free -m 2>/dev/null | awk 'NR==2{printf \"%d\", $3*100/$2}')",
        "disk=$(df -P / 2>/dev/null | tail -1 | awk '{print $5}' | tr -d '%')",
        'echo "load=$load cores=$cores mem=${mem:-0}% disk=${disk:-0}%"',
        '[ "$(echo "$load" | cut -d. -f1)" -le "$(( cores * ' + str(load_max) + ' ))" ] || ' + _fail_tag("LOAD_FAIL", "load=${load} > cores*" + str(load_max) + " (cores=${cores})"),
        '[ "${mem:-0}" -le "' + str(mem_max) + '" ] || ' + _fail_tag("MEM_FAIL", "mem=${mem}% > " + str(mem_max) + "%"),
        '[ "${disk:-0}" -le "' + str(disk_max) + '" ] || ' + _fail_tag("DISK_FAIL", "disk=${disk}% > " + str(disk_max) + "%"),
    ]
    return "\n".join(script)



def _fail_tag(label: str, detail: str) -> str:
    # emit a single-line then exit 1 (kept separate so the `[ ] ||` idiom works)
    return f'{{ echo "{label}:{detail}"; exit 1; }}'


# ---------------------------------------------------------------------------
# 系统服务健康检查（mysql/nginx/keepalived/haproxy + 通用 systemd）
# ---------------------------------------------------------------------------
SERVICE_HEALTH: dict[str, list[str]] = {
    "nginx": ['if out=$(nginx -t 2>&1); then echo "nginx_config=ok"; else echo "nginx_config=fail"; echo "$out" | head -5; exit 1; fi'],
    "mysql": ['if out=$(mysqladmin ping 2>&1); then echo "$out" | grep -q alive && echo "mysql=alive" || { echo "mysql=not_alive: $out"; exit 1; }; else echo "mysqladmin_cmd_fail"; exit 1; fi'],
    # keepalived / others: rely on systemd active + port probe
}



# haproxy health: binary may not be on PATH (launched by systemd ExecStart) — resolve real path.
_HAPROXY_PROBE = r"""
if out=$(HB=$(systemctl show haproxy -p ExecStart --value 2>/dev/null); HB=${HB%% *}; [ -n "$HB" ] && "$HB" -c -f /etc/haproxy/haproxy.cfg 2>&1 || command -v haproxy >/dev/null 2>&1 && haproxy -c -f /etc/haproxy/haproxy.cfg 2>&1 || echo 'haproxy binary not found'); then echo "haproxy_config=ok"; else echo "haproxy_config=fail"; echo "$out" | head -6; exit 1; fi
"""

def service_script(name: str, cfg: dict, os_flavor: str) -> str:
    svc = shlex.quote(name)
    script = [
        f'echo "service={name} os={os_flavor}"',
        f'if systemctl is-active --quiet {svc} 2>/dev/null; then echo "status=active"; else echo "status=inactive"; exit 1; fi',
    ]
    if name in SERVICE_HEALTH:
        script.extend(SERVICE_HEALTH[name])
    if name == "haproxy":
        script.append(_HAPROXY_PROBE)
    port = _num(cfg, "port", 0)
    if port:
        script.append(f'if ss -ltn 2>/dev/null | grep -q ":{port} "; then echo "port_{port}=open"; else echo "port_{port}=closed"; exit 1; fi')
    return "\n".join(script)


# ---------------------------------------------------------------------------
# K8s 集群组件 + Pod 检查（经跳板机对控制面节点跑 kubectl）
# ---------------------------------------------------------------------------
def cluster_script(cfg: dict) -> str:
    script = [
        "echo '--- k8s nodes ---'",
        "nodes=$(kubectl get nodes --no-headers 2>/dev/null | wc -l)",
        "notready=$(kubectl get nodes --no-headers 2>/dev/null | grep -c NotReady)",
        "pods=$(kubectl get pods -A --no-headers 2>/dev/null | wc -l)",
        "notrunning=$(kubectl get pods -A --no-headers 2>/dev/null | grep -vc Running)",
        'echo "nodes=$nodes notready=$notready pods=$pods notrunning=$notrunning"',
        '[ "$notready" -eq 0 ] || { echo "NODE_FAIL:notready=$notready"; exit 1; }',
        '[ "$notrunning" -eq 0 ] || { echo "POD_FAIL:notrunning=$notrunning"; exit 1; }',
    ]
    return "\n".join(script)


def pod_script(ns: str, pod: str) -> str:
    ns, pod = shlex.quote(ns), shlex.quote(pod)
    script = [
        f"phase=$(kubectl -n {ns} get pod {pod} -o jsonpath='{{.status.phase}}' 2>/dev/null)",
        f"ready=$(kubectl -n {ns} get pod {pod} -o jsonpath='{{.status.conditions[?(@.type==\\\"Ready\\\")].status}}' 2>/dev/null)",
        f"rc=$(kubectl -n {ns} get pod {pod} -o jsonpath='{{.status.containerStatuses[0].restartCount}}' 2>/dev/null)",
        'echo "pod=' + ns + '/' + pod + ' phase=$phase ready=$ready restart=$rc"',
        '[ "$phase" = "Running" ] && [ "$ready" = "True" ] || { echo "POD_FAIL:phase=$phase ready=$ready"; exit 1; }',
    ]
    return "\n".join(script)


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------
def build_check_script(check_item: CheckItem, target: TargetObject, os_flavor: str | None) -> str:
    cfg = _config(check_item)
    tt = target.object_type
    if tt == "physical":
        return resource_script(cfg, os_flavor or "unknown")
    if tt == "service":
        name = target.object_name.split("@")[0]
        return service_script(name, cfg, os_flavor or "unknown")
    if tt == "cluster":
        return cluster_script(cfg)
    if tt == "pod":
        ns, _, pod = target.object_name.partition("/")
        return pod_script(ns, pod)
    return "true"  # unknown target type -> trivial probe
