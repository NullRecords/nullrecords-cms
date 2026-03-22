"""Playlist ORM model."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String

from app.core.database import Base


class Playlist(Base):
    __tablename__ = "playlists"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    platform = Column(String, nullable=False, index=True)
    curator_name = Column(String, default="")
    followers = Column(Integer, default=0)
    contact = Column(String, default="")
    url = Column(String, default="")
    relevance_score = Column(Float, default=0.0)
    last_contacted = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
