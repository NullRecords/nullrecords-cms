"""Influencer ORM model."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String

from app.core.database import Base


class Influencer(Base):
    __tablename__ = "influencers"

    id = Column(Integer, primary_key=True, index=True)
    handle = Column(String, nullable=False)
    platform = Column(String, nullable=False, index=True)
    followers = Column(Integer, default=0)
    niche = Column(String, default="")
    contact = Column(String, default="")
    relevance_score = Column(Float, default=0.0)
    last_contacted = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
