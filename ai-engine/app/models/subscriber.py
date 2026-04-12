"""Subscriber ORM model — CRM contact for the NullRecords mailing list."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from app.core.database import Base


class Subscriber(Base):
    __tablename__ = "subscribers"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=True)
    source = Column(String, default="website")  # homepage | store | contact | youtube | manual
    tags = Column(Text, default="")  # comma-separated: "lead-magnet,buyer,newsletter"
    status = Column(String, default="active")  # active | unsubscribed | bounced
    brevo_contact_id = Column(String, nullable=True)  # Brevo contact ID after sync
    lead_magnet_sent = Column(Boolean, default=False)
    confirmed = Column(Boolean, default=False)  # double opt-in confirmed
    unsubscribed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
