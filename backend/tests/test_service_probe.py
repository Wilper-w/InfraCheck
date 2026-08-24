"""系统服务探测方式与启用/停用（CONTRACT §3/§4/§6）。"""
from __future__ import annotations

from app.engine.targets import TargetObject, resolve_targets
from app.models import CheckItem, SystemService
from app.runner.ssh import _command_for


def _svc_target(mode: str, *, port: int | None = None, vip: str | None = None) -> TargetObject:
    return TargetObject(
        "service", "keepalived@env1", 1, "ubuntu", "10.0.1.1",
        probe_mode=mode, probe_target=vip, probe_port=port,
    )


def _item() -> CheckItem:
    return CheckItem(id=1, name="服务存活", target_type="service", enabled=True, config="{}")


def test_systemd_mode_uses_systemctl():
    cmd = _command_for(_item(), _svc_target("systemd"))
    assert "systemctl is-active --quiet keepalived" in cmd


def test_port_mode_checks_listening_socket():
    cmd = _command_for(_item(), _svc_target("port", port=3306))
    assert "3306" in cmd and "LISTEN" in cmd


def test_vip_mode_checks_address_binding():
    """keepalived：进程活着但 VIP 不在本机也算异常，所以查的是地址绑定。"""
    cmd = _command_for(_item(), _svc_target("vip", vip="10.0.1.250"))
    assert cmd == "ip -o addr show | grep -qw 10.0.1.250"


def test_port_mode_without_port_falls_back_to_systemd():
    """端口缺失时不能拼出 ':None' 这种坏命令，回落到 systemd。"""
    cmd = _command_for(_item(), _svc_target("port", port=None))
    assert "systemctl is-active --quiet keepalived" in cmd


def test_disabled_service_is_excluded_from_targets(db_session):
    """enabled 必须真正影响巡检范围，否则「停用」只是个摆设。"""
    from app.models import Environment

    env = Environment(name="probe-env", os_flavor="ubuntu", description="")
    db_session.add(env)
    db_session.flush()
    db_session.add_all([
        SystemService(environment_id=env.id, name="on-svc", enabled=True, probe_mode="systemd"),
        SystemService(environment_id=env.id, name="off-svc", enabled=False, probe_mode="systemd"),
    ])
    item = CheckItem(name="svc", target_type="service", enabled=True, config="{}")
    db_session.add(item)
    db_session.flush()

    names = {t.object_name.split("@")[0] for t in resolve_targets(db_session, item)}
    assert "on-svc" in names
    assert "off-svc" not in names


def test_toggle_endpoint_flips_enabled(client, auth_headers):
    envs = client.get("/api/environments", headers=auth_headers).json()["items"]
    env_id = envs[0]["id"]
    svc = client.post(
        f"/api/environments/{env_id}/services",
        json={"name": "toggle-me", "port": 8080, "probe_mode": "port"},
        headers=auth_headers,
    ).json()
    assert svc["enabled"] is True

    off = client.post(
        f"/api/environments/{env_id}/services/{svc['id']}/toggle", headers=auth_headers
    ).json()
    assert off["enabled"] is False

    on = client.post(
        f"/api/environments/{env_id}/services/{svc['id']}/toggle", headers=auth_headers
    ).json()
    assert on["enabled"] is True


def test_vip_mode_requires_target(client, auth_headers):
    envs = client.get("/api/environments", headers=auth_headers).json()["items"]
    env_id = envs[0]["id"]
    resp = client.post(
        f"/api/environments/{env_id}/services",
        json={"name": "bad-vip", "probe_mode": "vip"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_port_mode_requires_port(client, auth_headers):
    envs = client.get("/api/environments", headers=auth_headers).json()["items"]
    env_id = envs[0]["id"]
    resp = client.post(
        f"/api/environments/{env_id}/services",
        json={"name": "bad-port", "probe_mode": "port"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_update_service_probe_mode(client, auth_headers):
    envs = client.get("/api/environments", headers=auth_headers).json()["items"]
    env_id = envs[0]["id"]
    svc = client.post(
        f"/api/environments/{env_id}/services",
        json={"name": "upd", "probe_mode": "systemd"},
        headers=auth_headers,
    ).json()

    updated = client.put(
        f"/api/environments/{env_id}/services/{svc['id']}",
        json={"probe_mode": "vip", "probe_target": "10.9.9.9"},
        headers=auth_headers,
    ).json()
    assert updated["probe_mode"] == "vip"
    assert updated["probe_target"] == "10.9.9.9"

    # 改成 vip 却不给地址 → 422，避免产出无法执行的探测命令
    bad = client.put(
        f"/api/environments/{env_id}/services/{svc['id']}",
        json={"probe_mode": "vip", "probe_target": "  "},
        headers=auth_headers,
    )
    assert bad.status_code == 422
