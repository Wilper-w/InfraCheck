"""Pytest fixtures: isolated in-memory SQLite app + TestClient.

We override app.db's engine + SessionLocal BEFORE importing the app, so that
both the lifespan (create_all + seed) and get_db share one in-memory DB.
StaticPool keeps a single connection so the in-memory DB is shared across threads.
"""
from __future__ import annotations

import os

# Force dryrun + disable scheduler + mock auth for tests (set before any app import)
os.environ["RUNNER_TRANSPORT"] = "dryrun"
os.environ["SCHEDULER_ENABLED"] = "false"
os.environ["AUTH_MODE"] = "mock"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture(scope="session")
def app():
    # Override the DB engine + session to an isolated in-memory SQLite *before*
    # importing app.main, so the lifespan create_all/seed and get_db all use it.
    from app import config
    config.SCHEDULER_ENABLED = False
    config.DATABASE_URL = "sqlite:///:memory:"

    from app import db as db_module
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session)
    db_module.engine = engine
    db_module.SessionLocal = SessionLocal

    # Import models so their tables register on Base.metadata before create_all.
    import app.models  # noqa: F401  (registers all ORM models)
    from app.db import Base
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        from app.seed import seed
        seed(db)
    finally:
        db.close()

    from app.main import app

    # get_db already yields from db_module.SessionLocal (now in-memory), so no
    # dependency override is needed.
    yield app

    engine.dispose()


@pytest.fixture(scope="session")
def client(app):
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def token(client):
    """Login and return a Bearer token (CONTRACT §4 /auth/login)."""
    resp = client.post("/api/auth/login", json={"account": "zhangsan"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["account"] == "zhangsan"
    assert data["token"]
    return data["token"]


@pytest.fixture(scope="session")
def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}
