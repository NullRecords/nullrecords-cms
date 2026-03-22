"""Pydantic schemas for outreach and credentials."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class OutreachLogOut(BaseModel):
    id: int
    target_type: str
    target_id: int
    message: str
    status: str
    follow_up_date: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class OutreachSendRequest(BaseModel):
    target_type: str  # "playlist" | "influencer"
    target_id: int
    message: str


class CredentialCreate(BaseModel):
    service: str
    api_key: str
    extra_json: str = "{}"


class CredentialOut(BaseModel):
    id: int
    service: str
    # api_key intentionally omitted from default output
    extra_json: str

    model_config = {"from_attributes": True}
