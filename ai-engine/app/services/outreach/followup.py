"""Follow-up scheduling and retrieval."""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.outreach import OutreachLog


def schedule_follow_up(db: Session, outreach_id: int, days: int = 5) -> OutreachLog:
    """Set the follow-up date on an existing outreach log entry."""
    log = db.query(OutreachLog).filter(OutreachLog.id == outreach_id).first()
    if log is None:
        raise ValueError(f"OutreachLog {outreach_id} not found")
    log.follow_up_date = datetime.now(timezone.utc) + timedelta(days=days)
    db.commit()
    db.refresh(log)
    return log


def get_pending_followups(db: Session) -> list[OutreachLog]:
    """Return all outreach entries whose follow-up date is now or past."""
    now = datetime.now(timezone.utc)
    return (
        db.query(OutreachLog)
        .filter(
            OutreachLog.follow_up_date.isnot(None),
            OutreachLog.follow_up_date <= now,
            OutreachLog.status.in_(["pending", "sent"]),
        )
        .all()
    )
