"""Job scheduler — placeholder for background tasks.

Phase 2 will add scheduled media ingestion, follow-up reminders, and
automated content generation pipelines.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def run_pending_followups():
    """Check for and log due follow-ups. Call from a cron or manual trigger."""
    from app.core.database import SessionLocal
    from app.services.outreach.followup import get_pending_followups

    db = SessionLocal()
    try:
        due = get_pending_followups(db)
        if not due:
            logger.info("No follow-ups due at %s", datetime.now(timezone.utc).isoformat())
            return []
        for log in due:
            logger.info(
                "Follow-up due: outreach_id=%d target=%s/%d",
                log.id, log.target_type, log.target_id,
            )
        return due
    finally:
        db.close()
