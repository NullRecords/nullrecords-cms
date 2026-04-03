"""Email tracking routes: open pixel, Brevo webhooks, and status lookup."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.outreach import OutreachLog

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tracking", tags=["tracking"])

# 1x1 transparent PNG pixel
PIXEL = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


@router.get("/open/{outreach_id}.png")
def track_open(outreach_id: int, db: Session = Depends(get_db)):
    """Tracking pixel — records when an email is opened."""
    log = db.query(OutreachLog).filter(OutreachLog.id == outreach_id).first()
    if log and not log.opened_at:
        log.opened_at = datetime.now(timezone.utc)
        if log.status in ("sent", "delivered"):
            log.status = "opened"
        db.commit()
        logger.info("Email open tracked for outreach #%d", outreach_id)
    return Response(content=PIXEL, media_type="image/png", headers={
        "Cache-Control": "no-store, no-cache, must-revalidate",
        "Pragma": "no-cache",
    })


@router.post("/webhook/brevo")
async def brevo_webhook(request: Request, db: Session = Depends(get_db)):
    """Brevo transactional email webhook — receives delivery, open, click events.

    Configure in Brevo dashboard → Transactional → Settings → Webhook URL:
    https://your-domain.com/tracking/webhook/brevo
    """
    try:
        events = await request.json()
    except Exception:
        return {"status": "invalid payload"}

    # Brevo sends a single event object or a list
    if isinstance(events, dict):
        events = [events]

    processed = 0
    for event in events:
        message_id = event.get("message-id") or event.get("messageId", "")
        event_type = event.get("event", "")

        if not message_id:
            continue

        log = db.query(OutreachLog).filter(OutreachLog.message_id == message_id).first()
        if not log:
            continue

        now = datetime.now(timezone.utc)

        if event_type == "delivered" and not log.delivered_at:
            log.delivered_at = now
            if log.status in ("sent", "pending"):
                log.status = "delivered"
            processed += 1

        elif event_type in ("opened", "unique_opened") and not log.opened_at:
            log.opened_at = now
            if log.status in ("sent", "delivered"):
                log.status = "opened"
            processed += 1

        elif event_type == "click" and not log.clicked_at:
            log.clicked_at = now
            if log.status in ("sent", "delivered", "opened"):
                log.status = "clicked"
            processed += 1

        elif event_type in ("hard_bounce", "soft_bounce", "blocked", "invalid"):
            log.status = "failed"
            processed += 1

    if processed:
        db.commit()

    logger.info("Brevo webhook: processed %d events", processed)
    return {"status": "ok", "processed": processed}


@router.get("/status/{outreach_id}")
def tracking_status(outreach_id: int, db: Session = Depends(get_db)):
    """Get detailed tracking status for an outreach entry."""
    log = db.query(OutreachLog).filter(OutreachLog.id == outreach_id).first()
    if not log:
        return {"error": "not found"}
    return {
        "id": log.id,
        "status": log.status,
        "message_id": log.message_id,
        "delivered_at": log.delivered_at.isoformat() if log.delivered_at else None,
        "opened_at": log.opened_at.isoformat() if log.opened_at else None,
        "clicked_at": log.clicked_at.isoformat() if log.clicked_at else None,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }
