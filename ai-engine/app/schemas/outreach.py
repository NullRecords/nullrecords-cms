"""Pydantic schemas for outreach and credentials."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class OutreachLogOut(BaseModel):
    id: int
    target_type: str
    target_id: int
    subject: str = ""
    message: str
    status: str
    message_id: Optional[str] = None
    follow_up_date: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    clicked_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class OutreachSendRequest(BaseModel):
    target_type: str  # "playlist" | "influencer"
    target_id: int
    message: str


class BatchOutreachTarget(BaseModel):
    target_type: str  # "playlist" | "influencer"
    target_id: int
    message: Optional[str] = None  # auto-generated if omitted


class BatchOutreachRequest(BaseModel):
    targets: list[BatchOutreachTarget]


class BatchOutreachResult(BaseModel):
    total: int
    sent: int
    logged: int


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
