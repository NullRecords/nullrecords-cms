"""OutreachLog ORM model."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.core.database import Base


class OutreachLog(Base):
    __tablename__ = "outreach_logs"

    id = Column(Integer, primary_key=True, index=True)
    target_type = Column(String, nullable=False)  # "playlist" or "influencer"
    target_id = Column(Integer, nullable=False)
    subject = Column(String, default="")
    message = Column(Text, default="")
    status = Column(String, default="pending")  # pending | sent | delivered | opened | clicked | replied | failed | logged
    message_id = Column(String, nullable=True)  # Brevo message ID for tracking
    follow_up_date = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    opened_at = Column(DateTime, nullable=True)
    clicked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
