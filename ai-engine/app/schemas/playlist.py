"""Pydantic schemas for playlists and influencers."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PlaylistOut(BaseModel):
    id: int
    name: str
    platform: str
    curator_name: str
    followers: int
    contact: str
    url: str
    relevance_score: float
    last_contacted: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class InfluencerOut(BaseModel):
    id: int
    handle: str
    platform: str
    followers: int
    niche: str
    contact: str
    relevance_score: float
    last_contacted: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DiscoverRequest(BaseModel):
    query: str
