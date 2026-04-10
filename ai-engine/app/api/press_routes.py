"""Press release system API routes."""

import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from app.services.press.brand_profile import (
    get_brand_summary,
    load_brand_profile,
    save_brand_profile,
)
from app.services.press.press_campaign import (
    add_contacts_to_campaign,
    create_campaign,
    distribute_campaign,
    get_campaign,
    list_campaigns,
    update_campaign_press_release,
)
from app.services.press.press_discovery import (
    discover_press_contacts,
    enrich_all_press_contacts,
    load_press_contacts,
    merge_press_contacts,
    save_press_contacts,
)
from app.services.press.press_generator import generate_press_release, list_event_types

log = logging.getLogger(__name__)

router = APIRouter(prefix="/press", tags=["press"])


# ── Schemas ─────────────────────────────────────────────────────────────

class DiscoverRequest(BaseModel):
    vertical: str | None = None
    searches: list[str] | None = None
    max_per_search: int = 8


class CampaignCreateRequest(BaseModel):
    name: str
    event_type: str
    vertical: str
    release_info: dict[str, Any] = Field(default_factory=dict)
    generate: bool = True
    contact_filter: dict | None = None


class PressReleaseRequest(BaseModel):
    event_type: str
    release_info: dict[str, Any] = Field(default_factory=dict)
    vertical: str | None = None


class DistributeRequest(BaseModel):
    max_per_run: int = 50


class ContactUpdateRequest(BaseModel):
    hash: str
    email: str | None = None
    status: str | None = None
    confidence_score: float | None = None


class AddContactsRequest(BaseModel):
    contact_hashes: list[str]


class PressReleaseUpdateRequest(BaseModel):
    subject: str
    body_text: str
    body_html: str
    boilerplate: str = ""


# ── Brand Profile ───────────────────────────────────────────────────────

@router.get("/brand-profile")
def get_brand_profile():
    """Get the current brand profile configuration."""
    return load_brand_profile()


@router.put("/brand-profile")
def update_brand_profile(profile: dict[str, Any]):
    """Update the brand profile."""
    save_brand_profile(profile)
    return {"status": "updated"}


@router.get("/brand-summary")
def get_summary(vertical: str | None = None):
    """Get a text summary of the brand (for display/debugging)."""
    return {"summary": get_brand_summary(vertical)}


# ── Event Types ─────────────────────────────────────────────────────────

@router.get("/event-types")
def get_event_types():
    """List available press event types."""
    return list_event_types()


# ── Press Release Generation ────────────────────────────────────────────

@router.post("/generate")
def generate_release(req: PressReleaseRequest):
    """Generate a press release (without creating a campaign)."""
    result = generate_press_release(req.event_type, req.release_info, req.vertical)
    return result


# ── Discovery ───────────────────────────────────────────────────────────

@router.post("/discover")
def run_discovery(req: DiscoverRequest, background_tasks: BackgroundTasks):
    """Discover new press contacts. Runs in background and merges results."""
    def _discover():
        new = discover_press_contacts(
            vertical_id=req.vertical,
            max_per_search=req.max_per_search,
            searches=req.searches,
        )
        if new:
            result = merge_press_contacts(new)
            log.info("Discovery complete: %d added, %d total", result["added"], result["total"])

    background_tasks.add_task(_discover)
    return {"status": "discovery_started", "vertical": req.vertical}


@router.post("/discover/sync")
def run_discovery_sync(req: DiscoverRequest):
    """Discover new press contacts synchronously (returns the results)."""
    new = discover_press_contacts(
        vertical_id=req.vertical,
        max_per_search=req.max_per_search,
        searches=req.searches,
    )
    result = merge_press_contacts(new) if new else {"added": 0, "total": 0}
    return {"contacts_found": len(new), **result}


@router.post("/enrich")
def run_enrichment(max_enrich: int = 20):
    """Try to find emails for contacts missing them."""
    enriched = enrich_all_press_contacts(max_enrich)
    return {"enriched": enriched}


# ── Contacts ────────────────────────────────────────────────────────────

@router.get("/contacts")
def get_contacts(
    vertical: str | None = None,
    contact_type: str | None = None,
    has_email: bool | None = None,
    status: str | None = None,
):
    """List press contacts with optional filters."""
    contacts = load_press_contacts()

    if vertical:
        contacts = [c for c in contacts if c.get("vertical") == vertical]
    if contact_type:
        contacts = [c for c in contacts if c.get("type") == contact_type]
    if has_email is True:
        contacts = [c for c in contacts if c.get("email")]
    elif has_email is False:
        contacts = [c for c in contacts if not c.get("email")]
    if status:
        contacts = [c for c in contacts if c.get("status") == status]

    return {"contacts": contacts, "total": len(contacts)}


@router.put("/contacts")
def update_contact(req: ContactUpdateRequest):
    """Update a specific contact field."""
    contacts = load_press_contacts()
    updated = False
    for c in contacts:
        if c["hash"] == req.hash:
            if req.email is not None:
                c["email"] = req.email
            if req.status is not None:
                c["status"] = req.status
            if req.confidence_score is not None:
                c["confidence_score"] = req.confidence_score
            updated = True
            break

    if not updated:
        raise HTTPException(status_code=404, detail="Contact not found")

    save_press_contacts(contacts)
    return {"status": "updated"}


@router.delete("/contacts/{contact_hash}")
def delete_contact(contact_hash: str):
    """Remove a contact from the press list."""
    contacts = load_press_contacts()
    before = len(contacts)
    contacts = [c for c in contacts if c["hash"] != contact_hash]
    if len(contacts) == before:
        raise HTTPException(status_code=404, detail="Contact not found")
    save_press_contacts(contacts)
    return {"status": "deleted"}


# ── Campaigns ───────────────────────────────────────────────────────────

@router.get("/campaigns")
def get_campaigns():
    """List all campaigns (summary view)."""
    return list_campaigns()


@router.get("/campaigns/{campaign_id}")
def get_campaign_detail(campaign_id: str):
    """Get full campaign details."""
    campaign = get_campaign(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.post("/campaigns")
def create_new_campaign(req: CampaignCreateRequest):
    """Create a new press campaign (generates press release + selects contacts)."""
    campaign = create_campaign(
        name=req.name,
        event_type=req.event_type,
        vertical=req.vertical,
        release_info=req.release_info,
        generate=req.generate,
        contact_filter=req.contact_filter,
    )
    return campaign


@router.put("/campaigns/{campaign_id}/press-release")
def edit_press_release(campaign_id: str, req: PressReleaseUpdateRequest):
    """Edit the press release content for a campaign."""
    campaign = update_campaign_press_release(campaign_id, req.model_dump())
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return {"status": "updated"}


@router.post("/campaigns/{campaign_id}/contacts")
def add_contacts(campaign_id: str, req: AddContactsRequest):
    """Add more contacts to a campaign."""
    campaign = add_contacts_to_campaign(campaign_id, req.contact_hashes)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return {"status": "added", "total_contacts": len(campaign["contacts"])}


@router.post("/campaigns/{campaign_id}/distribute")
def distribute(campaign_id: str, req: DistributeRequest | None = None):
    """Send the press release to contacts in the campaign."""
    max_per_run = req.max_per_run if req else 50
    result = distribute_campaign(campaign_id, max_per_run)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
