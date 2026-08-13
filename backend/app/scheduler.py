"""APScheduler manager: time-point (cron) based periodic inspection.

Schedules are a list of entries, each {time: "HH:MM", days: [0..6]} where an
empty days list means every day. Fully configurable from the UI at runtime:
changing the schedule rebuilds the APScheduler jobs without a restart.
"""
from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from app import config, settings as kv
from app.models import Run

_scheduler: BackgroundScheduler | None = None
_JOB_PREFIX = "auto_inspection_"


def _scheduled_run() -> None:
    """Run a full inspection on schedule (actor = 'scheduler')."""
    from app.db import SessionLocal
    from app.engine import execute_run
    from app.models import AuditLog

    db: Session = SessionLocal()
    try:
        run = Run(trigger="scheduled", triggered_by="scheduler", status="running")
        db.add(run)
        db.flush()
        db.add(
            AuditLog(
                actor="scheduler",
                action="run.trigger",
                target_ref=f"run:{run.id}",
                detail="scheduled time-point inspection triggered",
            )
        )
        db.commit()
        db.refresh(run)
        execute_run(db, run, "scheduler")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _cron_trigger(entry: dict) -> CronTrigger:
    """Build a CronTrigger from a schedule entry."""
    hour, minute = (int(x) for x in entry["time"].split(":"))
    kwargs: dict = {"hour": hour, "minute": minute}
    days = entry.get("days") or []
    if days:
        # APScheduler day_of_week: 0=Mon .. 6=Sun
        kwargs["day_of_week"] = ",".join(str(int(d) % 7) for d in days)
    return CronTrigger(**kwargs)


def _rebuild(enabled: bool, schedules: list[dict]) -> None:
    """Remove all auto-inspection jobs then add one per schedule (if enabled)."""
    global _scheduler
    if _scheduler is None:
        return
    for job in [j for j in _scheduler.get_jobs() if j.id.startswith(_JOB_PREFIX)]:
        job.remove()
    if not enabled or not schedules:
        return
    for i, entry in enumerate(schedules):
        _scheduler.add_job(
            _scheduled_run,
            trigger=_cron_trigger(entry),
            id=f"{_JOB_PREFIX}{i}",
            replace_existing=True,
            coalesce=True,
        )


def start_scheduler(db: Session) -> None:
    """Create + start the scheduler using current DB settings (call once at boot)."""
    global _scheduler
    if _scheduler is not None:
        return
    enabled = kv.get_bool(db, kv.AUTO_INSPECTION_ENABLED, config.SCHEDULER_ENABLED)
    schedules = kv.get_schedules(db)
    _scheduler = BackgroundScheduler()
    _scheduler.start()
    _rebuild(enabled, schedules)


def apply_scheduler(enabled: bool, schedules: list[dict]) -> None:
    """Rebuild the scheduled jobs from the new config (safe if absent)."""
    _rebuild(enabled, schedules)


def get_state(db: Session) -> dict:
    """Return scheduler state for the API."""
    enabled = kv.get_bool(db, kv.AUTO_INSPECTION_ENABLED, config.SCHEDULER_ENABLED)
    schedules = kv.get_schedules(db)
    next_times: list[dict] = []
    if _scheduler is not None:
        jobs = sorted(
            (j for j in _scheduler.get_jobs() if j.id.startswith(_JOB_PREFIX)),
            key=lambda j: int(j.id[len(_JOB_PREFIX):]),
        )
        for i, job in enumerate(jobs):
            entry = schedules[i] if i < len(schedules) else {}
            next_times.append(
                {
                    "time": entry.get("time", ""),
                    "days": entry.get("days", []),
                    "next_run_at": job.next_run_time.isoformat() if job.next_run_time else None,
                }
            )
    last_run = (
        db.query(Run).filter(Run.trigger == "scheduled").order_by(Run.id.desc()).first()
    )
    return {
        "enabled": enabled,
        "schedules": schedules,
        "next_run_times": next_times,
        "last_scheduled_run_at": last_run.started_at.isoformat() if last_run else None,
    }


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
