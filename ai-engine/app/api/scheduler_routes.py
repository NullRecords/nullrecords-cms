"""Scheduler admin API routes — status, trigger, and control."""

from fastapi import APIRouter, HTTPException

from app.jobs.scheduler import (
    get_scheduler_status,
    start_scheduler,
    stop_scheduler,
    trigger_job,
)

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


@router.get("/status")
def status():
    """Return scheduler status and all registered jobs."""
    return get_scheduler_status()


@router.post("/start")
def start():
    """Start the scheduler (if not already running)."""
    start_scheduler()
    return get_scheduler_status()


@router.post("/stop")
def stop():
    """Stop the scheduler."""
    stop_scheduler()
    return {"running": False}


@router.post("/trigger/{job_id}")
def trigger(job_id: str):
    """Trigger a specific job to run immediately.

    Valid job_ids: followup_check, source_discovery, media_ingest
    """
    ok = trigger_job(job_id)
    if not ok:
        raise HTTPException(
            status_code=404,
            detail=f"Job '{job_id}' not found or scheduler not running",
        )
    return {"triggered": job_id}
