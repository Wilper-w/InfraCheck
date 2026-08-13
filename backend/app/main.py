"""FastAPI application entrypoint (CONTRACT §1, §2, §8)."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.api import (
    auth,
    check_items,
    dashboard,
    findings,
    inventory,
    reports_audit,
    runs,
    settings as settings_api,
)
from app.db import Base, engine
from app.scheduler import shutdown_scheduler, start_scheduler
from app.seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    # create tables + seed on startup
    Base.metadata.create_all(bind=engine)
    from app.db import SessionLocal
    db = SessionLocal()
    try:
        seed(db)
        # init the periodic scheduler from DB settings (runtime-configurable)
        start_scheduler(db)
    finally:
        db.close()
    yield
    shutdown_scheduler()


app = FastAPI(title="InfraCheck API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# all routers mounted under /api (CONTRACT §8)
api_prefix = "/api"
for r in (
    auth.router,
    inventory.router,
    check_items.router,
    runs.router,
    dashboard.router,
    reports_audit.reports_router,
    reports_audit.audit_router,
    settings_api.router,
    findings.router,
):
    app.include_router(r, prefix=api_prefix)


@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok"}
