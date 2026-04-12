"""Pydantic schemas for the CRM / subscriber endpoints."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class SubscribeRequest(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    source: str = "website"


class SubscriberOut(BaseModel):
    id: int
    email: str
    name: Optional[str] = None
    source: str
    tags: str
    status: str
    lead_magnet_sent: bool
    confirmed: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SubscriberUpdate(BaseModel):
    name: Optional[str] = None
    tags: Optional[str] = None
    status: Optional[str] = None


class UnsubscribeRequest(BaseModel):
    email: EmailStr


class BulkTagRequest(BaseModel):
    """Add a tag to multiple subscribers at once."""
    email_list: list[str]
    tag: str


class CRMStats(BaseModel):
    total: int
    active: int
    unsubscribed: int
    bounced: int
    lead_magnet_sent: int
    sources: dict[str, int]
