"""Runner transports (CONTRACT §6). dryrun default + real ssh via jump host ProxyJump.

- dryrun: deterministic, covers all four result states for local/demo use.
- ssh: real execution via asyncssh, connecting to the jump host and then
  opening a nested SSH connection through it (connect_ssh == ProxyJump) to the
  target, running an OS-dispatched command, and mapping exit status to a result.

One module per transport; `get_runner` picks one and everything is re-exported
here so callers keep using `from app.runner import X`.
"""
from __future__ import annotations

from app.runner.base import BaseRunner
from app.runner.dryrun import DryRunRunner
from app.runner.ssh import SshRunner

__all__ = ["BaseRunner", "DryRunRunner", "SshRunner", "get_runner"]


def get_runner(transport: str) -> BaseRunner:
    if transport == "ssh":
        return SshRunner()
    return DryRunRunner()
