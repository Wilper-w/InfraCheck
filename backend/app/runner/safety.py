"""Safety gate for remote inspection commands (CONTRACT §6).

Inspection commands run on real production nodes through the jump host, so we
must guarantee they are read-only. This module scans a generated shell script
for destructive / mutating operations and blocks it before it ever reaches the
node. All current checks (df/free/systemctl is-active/mysqladmin ping/kubectl
get/nginx -t/...) pass; anything risky is refused and flagged as abnormal.
"""
from __future__ import annotations

import re

# Destructive / mutating verbs, matched on word boundaries to avoid false hits
# inside benign words (e.g. the `dd` in "adding" or `kill` in "skill").
_BLOCKED_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("file-delete", re.compile(r"(?<![A-Za-z0-9_])(rm|rmdir|unlink)\b")),
    ("shutdown", re.compile(r"(?<![A-Za-z0-9_])(reboot|shutdown|halt|poweroff|init\s+0|init\s+6)\b")),
    ("disk-wipe", re.compile(r"(?<![A-Za-z0-9_])(mkfs|mkfs\.\w+|fdisk|parted|swapoff|mkswap)\b")),
    ("raw-write", re.compile(r"(?<![A-Za-z0-9_])(dd\b)")),
    ("process-kill", re.compile(r"(?<![A-Za-z0-9_])(kill|pkill|killall|killall5)\b")),
    ("service-stop", re.compile(r"(?<![A-Za-z0-9_])(systemctl|service)\s+(stop|restart|reload|disable|mask|halt|poweroff|reboot)\b")),
    ("db-drop", re.compile(r"(?<![A-Za-z0-9_])(drop\s+(table|database|index)|truncate\b)\b", re.IGNORECASE)),
    ("db-delete", re.compile(r"(?<![A-Za-z0-9_])(delete\s+from)\b", re.IGNORECASE)),
    ("perm-change", re.compile(r"(?<![A-Za-z0-9_])(chmod|chown|chattr)\b")),
    ("root-mount-write", re.compile(r"(?<![A-Za-z0-9_])(mount|umount|pvs|vgs|lvs)\b")),
    ("config-overwrite", re.compile(r"(?<![A-Za-z0-9_])(sed\s+-i|tee>|:>\s|>\s?/etc/|>>\s?/etc/)")),
    # write redirection of any kind to files under common system roots
    ("fs-write", re.compile(r"(?<![A-Za-z0-9_])(>|>>)\s+/(etc|var|usr|boot|root|srv)")),
]


def blocked_reason(script: str) -> str | None:
    """Return a reason string if the script contains a blocked operation, else None."""
    for name, pat in _BLOCKED_PATTERNS:
        if pat.search(script):
            return name
    return None
