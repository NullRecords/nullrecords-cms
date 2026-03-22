"""MediaAsset ORM model."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text

from app.core.database import Base


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, nullable=False, index=True)
    source_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    url = Column(String, nullable=False)
    preview_url = Column(String, default="")
    local_path = Column(String, nullable=True)
    tags = Column(Text, default="[]")  # JSON-encoded list
    mood = Column(String, default="")
    style = Column(String, default="")
    duration = Column(Float, default=0.0)
    downloaded = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
