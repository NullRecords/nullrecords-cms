"""OutreachLog ORM model."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.core.database import Base


class OutreachLog(Base):
    __tablename__ = "outreach_logs"

    id = Column(Integer, primary_key=True, index=True)
    target_type = Column(String, nullable=False)  # "playlist" or "influencer"
    target_id = Column(Integer, nullable=False)
    message = Column(Text, default="")
    status = Column(String, default="pending")  # pending | sent | replied | failed
    follow_up_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
