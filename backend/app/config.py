"""Application configuration loaded from environment variables (.env auto-loaded)."""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Auto-load backend/.env if present (python-dotenv). Real-inspection settings go here.
try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv(BASE_DIR / ".env")
except ImportError:  # dotenv optional; vars can be passed via shell env instead
    pass

# Database
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'infracheck.db'}")

# JWT
JWT_SECRET = os.getenv("JWT_SECRET", "infracheck-dev-secret-change-me-32bytes")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))

# Wecom SSO mode toggle (mock default works out-of-the-box)
AUTH_MODE = os.getenv("AUTH_MODE", "mock")  # mock | wecom

# Runner transport
RUNNER_TRANSPORT = os.getenv("RUNNER_TRANSPORT", "dryrun")  # dryrun | ssh
# Aggregated execution: "ansible" fans out on the gateway via collector_run
# (1 SSH per env), replacing per-node nested SSH for large fleets.
COLLECTOR = os.getenv("COLLECTOR", "").strip().lower()  # "" | ansible

# Bounded concurrency for a single run (ADR-0002 ~100-200; also paces work so
# thousands of nodes are never all hammering the jump host at once).
RUN_CONCURRENCY = int(os.getenv("RUN_CONCURRENCY", "100"))

# SSH transport settings (only used when RUNNER_TRANSPORT=ssh)
JUMP_HOST = os.getenv("JUMP_HOST", "")
JUMP_USER = os.getenv("JUMP_USER", "")
JUMP_KEY = os.getenv("JUMP_KEY", "")
SSH_USER = os.getenv("SSH_USER", "root")
SSH_KEY = os.getenv("SSH_KEY", JUMP_KEY)
SSH_PORT = int(os.getenv("SSH_PORT", "22"))
SSH_TIMEOUT = float(os.getenv("SSH_TIMEOUT", "15"))
# Optional known_hosts file for host-key verification (recommended for prod).
# Empty = no verification (dev default); set to a real file to harden against MITM.
KNOWN_HOSTS = os.getenv("KNOWN_HOSTS", "")

# Run inspection commands THROUGH the jump host's own ssh client via a host alias
# (jump host ~/.ssh/config), reusing its keys/agent. Set this when you reach
# environments only by an alias on the jump host (e.g. `ssh env-node1`).
SSH_VIA_JUMP_SHELL = os.getenv("SSH_VIA_JUMP_SHELL", "0").lower() in ("1", "true", "yes", "on")
SSH_VIA_JUMP_USER = os.getenv("SSH_VIA_JUMP_USER", "")
# Executable that reaches a node FROM the jump host (alias mode). Default: ssh <address>.
# Set to a command/wrapper that itself already runs ssh, e.g. `lf`; supports {address}.
SSH_NODE_COMMAND = os.getenv("SSH_NODE_COMMAND", "")
# Optional intermediate hop: nodes are only reachable via a gateway node that
# itself is reachable from JUMP. When set, node checks run as:
#   JUMP -> gateway -> node   (double-escaped, so multi-line cmds with quotes work)
SSH_GATEWAY = os.getenv("SSH_GATEWAY", "")
SSH_GATEWAY_PORT = int(os.getenv("SSH_GATEWAY_PORT", "22"))
SSH_GATEWAY_USER = os.getenv("SSH_GATEWAY_USER", "")

# Scheduler
SCHEDULER_ENABLED = os.getenv("SCHEDULER_ENABLED", "true").lower() == "true"
SCHEDULER_INTERVAL_MINUTES = int(os.getenv("SCHEDULER_INTERVAL_MINUTES", "60"))

# Seed demo assets on an empty DB. Set SEED_DEMO=false to start blank (real site).
SEED_DEMO = os.getenv("SEED_DEMO", "false").lower() in ("1", "true", "yes", "on")

# Documented default mysql auth (xunjian.md); override per-site.
MYSQL_DEFAULT_PW = os.getenv("MYSQL_DEFAULT_PW", "Cl0ud!P@ssw0rd")

# Reports output directory
REPORTS_OUT_DIR = Path(os.getenv("REPORTS_OUT_DIR", str(BASE_DIR / "reports_out")))
REPORTS_OUT_DIR.mkdir(parents=True, exist_ok=True)

# CORS
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
