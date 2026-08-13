"""Application configuration loaded from environment variables."""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

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

# Scheduler
SCHEDULER_ENABLED = os.getenv("SCHEDULER_ENABLED", "true").lower() == "true"
SCHEDULER_INTERVAL_MINUTES = int(os.getenv("SCHEDULER_INTERVAL_MINUTES", "60"))

# Reports output directory
REPORTS_OUT_DIR = Path(os.getenv("REPORTS_OUT_DIR", str(BASE_DIR / "reports_out")))
REPORTS_OUT_DIR.mkdir(parents=True, exist_ok=True)

# CORS
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
