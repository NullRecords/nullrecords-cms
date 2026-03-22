"""Pydantic schemas for media assets."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# --- Request schemas ---

class MediaSearchRequest(BaseModel):
    query: str
    source: str = "pexels"  # "pexels" | "internet_archive"


# --- Response schemas ---

class MediaAssetOut(BaseModel):
    id: int
    source: str
    source_id: str
    title: str
    url: str
    preview_url: str
    local_path: Optional[str] = None
    tags: str
    mood: str
    style: str
    duration: float
    downloaded: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class MediaSearchResult(BaseModel):
    """A single item returned from a source search before DB insertion."""
    source: str
    source_id: str
    title: str
    url: str
    preview_url: str
    duration: float
