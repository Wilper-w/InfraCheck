"""Safety gate tests: real check commands pass; destructive ops are blocked."""
from __future__ import annotations

from app import checks
from app.runner.safety import blocked_reason


class TestSafetyGate:
    def test_legit_check_scripts_pass(self):
        safe = [
            checks.resource_script({"disk": 80}, "ubuntu"),
            checks.service_script("nginx", {}, "ubuntu"),
            checks.service_script("mysql", {}, "ubuntu"),
            checks.service_script("haproxy", {}, "ubuntu"),
            checks.service_script("keepalived", {}, "ubuntu"),
            checks.cluster_script({}),
            checks.pod_script("default", "one-api"),
        ]
        for sc in safe:
            assert blocked_reason(sc) is None, f"should not block: {sc[:60]}"

    def test_destructive_ops_blocked(self):
        dangerous = [
            "df -P / && rm -rf /var/lib",
            "systemctl stop nginx",
            "systemctl restart nginx",
            "reboot",
            "killall nginx",
            "mysql -e 'drop table t'",
            "mysql -e 'delete from users'",
            "echo x > /etc/hosts",
            "mkfs.ext4 /dev/sda1",
            "chmod 777 /etc/passwd",
            "dd if=/dev/zero of=/dev/sda",
            "truncate -s 0 /var/log/x",
        ]
        for d in dangerous:
            assert blocked_reason(d) is not None, f"should have blocked: {d}"

    def test_benign_substrings_not_blocked(self):
        # ensure we don't trip on `dd`/`kill`/`rm` inside words
        benign = [
            "echo 'adding more disks'",
            "awk '{print $1}' skill level",
            "df -P /",
        ]
        for b in benign:
            assert blocked_reason(b) is None, f"false positive: {b}"
