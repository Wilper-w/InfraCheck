"""Transport tests: SshRunner is a REAL asyncssh connection attempt (not a stub),
and execute_run's concurrency is bounded by RUN_CONCURRENCY (ADR-0002)."""
from __future__ import annotations

import asyncio
import json

from app import config
from app.engine import TargetObject
from app.runner import SshRunner


def _item(**kw):
    from app.models import CheckItem

    return CheckItem(
        id=kw.get("id", 1),
        name=kw.get("name", "probe"),
        target_type=kw.get("target_type", "physical"),
    )


def _target(**kw):
    return TargetObject(
        kw.get("object_type", "physical"),
        kw.get("object_name", "node-x(10.0.0.1)"),
        kw.get("environment_id", 1),
        kw.get("os_flavor", "ubuntu"),
        kw.get("address", "10.0.0.1"),
        probe_mode=kw.get("probe_mode"),
        probe_target=kw.get("probe_target"),
        probe_port=kw.get("probe_port"),
    )


def test_ssh_runner_is_a_real_connection_attempt(monkeypatch):
    """Point the jump host at a closed port: the transport must genuinely
    attempt an asyncssh connect (yield connection_failed/timeout) instead of
    short-circuiting to a canned 'no_jump_host' stub."""
    monkeypatch.setattr(config, "JUMP_HOST", "127.0.0.1")
    monkeypatch.setattr(config, "SSH_PORT", 61234)  # closed -> connection refused
    monkeypatch.setattr(config, "SSH_TIMEOUT", 3)
    status, evidence = asyncio.run(SshRunner().execute(_item(), _target()))
    assert status == "unreachable"
    data = json.loads(evidence)
    assert data["transport"] == "ssh"
    assert data["verdict"] in ("connection_failed", "connection_timeout")
    assert data["verdict"] != "no_jump_host_configured"  # genuinely attempted


def test_ssh_runner_explicit_unreachable_without_jump_host(monkeypatch):
    # JUMP_HOST unset -> explicit reason, never a silent hang (isolated from .env)
    monkeypatch.setattr(config, "JUMP_HOST", "")
    status, evidence = asyncio.run(SshRunner().execute(_item(), _target()))
    assert status == "unreachable"
    assert json.loads(evidence)["verdict"] == "no_jump_host_configured"


def test_ssh_runner_without_address_is_unreachable(monkeypatch):
    monkeypatch.setattr(config, "JUMP_HOST", "127.0.0.1")
    status, evidence = asyncio.run(SshRunner().execute(_item(), _target(address=None)))
    assert status == "unreachable"
    assert json.loads(evidence)["verdict"] == "no_target_address"


def test_ssh_classify_maps_exit_code_to_status():
    # exit 0 => normal
    status, evidence = SshRunner._classify(_item(), _target(), 0, "host-a\n")
    assert status == "normal"
    assert json.loads(evidence)["verdict"] == "pass"
    # non-zero => abnormal (check ran and failed)
    status, evidence = SshRunner._classify(_item(name="nginx活性"), _target(), 3, "inactive\n")
    assert status == "abnormal"
    assert json.loads(evidence)["verdict"] == "command_nonzero"


def test_ssh_command_dispatched_by_target_type():
    from app.runner.ssh import _command_for
    from app import checks

    # systemd service -> health probe script containing systemctl + nginx -t
    svc = _command_for(_item(), _target(object_type="service", object_name="nginx@env1"))
    assert "systemctl is-active --quiet nginx" in svc
    assert "nginx -t" in svc
    # physical -> resource threshold script (disk check present)
    phys = _command_for(_item(), _target())
    assert "df -P /" in phys and "DISK_FAIL" in phys
    # port probe mode
    port_cmd = _command_for(_item(), _target(object_type="service", object_name="redis@env1", probe_mode="port", probe_port=6379))
    assert "6379" in port_cmd
    # pod -> kubectl script
    pod = _command_for(_item(), _target(object_type="pod", object_name="default/one-api"))
    assert "kubectl" in pod and "one-api" in pod
    # full scripts are valid shell
    import subprocess, tempfile, os
    for script in (svc, phys, pod, checks.cluster_script({})):
        with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as f:
            f.write(script); p_ = f.name
        r = subprocess.run(["bash", "-n", p_], capture_output=True)
        os.unlink(p_)
        assert r.returncode == 0, script


def test_run_concurrency_is_bounded(app, monkeypatch):
    counter = {"active": 0, "peak": 0}

    class TrackingRunner:
        async def execute(self, item, target):
            counter["active"] += 1
            counter["peak"] = max(counter["peak"], counter["active"])
            await asyncio.sleep(0.005)
            counter["active"] -= 1
            return "normal", '{"transport":"track"}'

    from app import db as db_module
    from app import runner as runner_module
    from app.engine import execute_run
    from app.models import Run

    monkeypatch.setattr(config, "RUN_CONCURRENCY", 2)
    monkeypatch.setattr(runner_module, "get_runner", lambda transport: TrackingRunner())

    db = db_module.SessionLocal()
    try:
        run = Run(trigger="manual", triggered_by="cgtest", status="running")
        db.add(run)
        db.flush()
        execute_run(db, run, "cgtest")
    finally:
        db.close()

    assert counter["peak"] >= 2        # parallelism genuinely happened
    assert counter["peak"] <= 2        # and the semaphore capped it at the bound
