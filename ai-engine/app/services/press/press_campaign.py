"""Press campaign manager — create, distribute, and track press release campaigns.

A campaign ties together a press release, a contact list, and distribution state.
Campaigns are stored as individual JSON files in exports/press/campaigns/.
"""

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.services.press.brand_profile import load_brand_profile
from app.services.press.press_discovery import load_press_contacts, save_press_contacts
from app.services.press.press_generator import generate_press_release

log = logging.getLogger(__name__)


def _campaigns_dir() -> Path:
    d = Path(get_settings().exports_dir) / "press" / "campaigns"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _campaign_path(campaign_id: str) -> Path:
    return _campaigns_dir() / f"{campaign_id}.json"


def _load_campaign(campaign_id: str) -> dict | None:
    p = _campaign_path(campaign_id)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return None


def _save_campaign(campaign: dict) -> None:
    p = _campaign_path(campaign["id"])
    p.write_text(json.dumps(campaign, indent=2, ensure_ascii=False), encoding="utf-8")


# ── Campaign CRUD ───────────────────────────────────────────────────────

def create_campaign(
    name: str,
    event_type: str,
    vertical: str,
    release_info: dict[str, Any],
    generate: bool = True,
    contact_filter: dict | None = None,
) -> dict:
    """Create a new press campaign.

    Parameters:
        name: Campaign display name
        event_type: One of the press_generator EVENT_TYPES
        vertical: 'music' or 'books'
        release_info: Dict with title, description, links, etc.
        generate: Auto-generate the press release (True) or leave blank for manual edit
        contact_filter: Optional filter for selecting contacts {types: [...], min_score: ...}

    Returns the full campaign dict.
    """
    campaign_id = datetime.now(timezone.utc).strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:8]

    press_release = None
    if generate:
        press_release = generate_press_release(event_type, release_info, vertical)

    # Select contacts for this campaign
    contacts = _select_contacts(vertical, contact_filter)

    campaign = {
        "id": campaign_id,
        "name": name,
        "event_type": event_type,
        "vertical": vertical,
        "release_info": release_info,
        "press_release": press_release,
        "status": "draft",
        "contacts": [
            {
                "hash": c["hash"],
                "name": c["name"],
                "email": c.get("email", ""),
                "type": c.get("type", ""),
                "send_status": "pending",
                "message_id": None,
                "sent_at": None,
            }
            for c in contacts
        ],
        "stats": {
            "total_contacts": len(contacts),
            "with_email": sum(1 for c in contacts if c.get("email")),
            "sent": 0,
            "delivered": 0,
            "opened": 0,
            "failed": 0,
        },
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "distributed_at": None,
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    _save_campaign(campaign)
    log.info("Created campaign %s with %d contacts", campaign_id, len(contacts))
    return campaign


def _select_contacts(vertical: str, contact_filter: dict | None = None) -> list[dict]:
    """Select press contacts matching a vertical and optional filter."""
    all_contacts = load_press_contacts()
    selected = []

    min_score = 0.0
    allowed_types = None
    if contact_filter:
        min_score = contact_filter.get("min_score", 0.0)
        allowed_types = contact_filter.get("types")

    for c in all_contacts:
        if c.get("vertical") != vertical and c.get("vertical") != "both":
            continue
        if c.get("confidence_score", 0.0) < min_score:
            continue
        if allowed_types and c.get("type") not in allowed_types:
            continue
        if c.get("status") == "blacklisted":
            continue
        selected.append(c)

    return selected


# ── Distribution ────────────────────────────────────────────────────────

def distribute_campaign(campaign_id: str, max_per_run: int = 50) -> dict:
    """Send press release to contacts in the campaign that haven't been sent yet.

    Uses existing email_sender (Brevo API + SMTP fallback).
    Returns {"sent": int, "failed": int, "skipped": int}.
    """
    from app.services.outreach.email_sender import send_email

    campaign = _load_campaign(campaign_id)
    if not campaign:
        return {"error": f"Campaign {campaign_id} not found"}
    if not campaign.get("press_release"):
        return {"error": "No press release generated for this campaign"}

    pr = campaign["press_release"]
    subject = pr["subject"]
    body_html = pr["body_html"]
    body_text = pr["body_text"]

    sent = 0
    failed = 0
    skipped = 0

    for contact in campaign["contacts"]:
        if sent >= max_per_run:
            break
        if contact["send_status"] != "pending":
            continue
        if not contact.get("email"):
            contact["send_status"] = "skipped_no_email"
            skipped += 1
            continue

        result = send_email(
            to_address=contact["email"],
            subject=subject,
            body=body_html,
        )

        if result.get("sent"):
            contact["send_status"] = "sent"
            contact["message_id"] = result.get("message_id")
            contact["sent_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            sent += 1
            # Update the master contacts list
            _update_contact_outreach(contact["hash"], campaign_id)
        else:
            contact["send_status"] = "failed"
            failed += 1

        time.sleep(0.5)  # rate limit

    # Update campaign stats
    campaign["stats"]["sent"] = sum(
        1 for c in campaign["contacts"] if c["send_status"] == "sent"
    )
    campaign["stats"]["failed"] = sum(
        1 for c in campaign["contacts"] if c["send_status"] == "failed"
    )
    campaign["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    if all(c["send_status"] != "pending" for c in campaign["contacts"]):
        campaign["status"] = "distributed"
        campaign["distributed_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    else:
        campaign["status"] = "distributing"

    _save_campaign(campaign)

    return {"sent": sent, "failed": failed, "skipped": skipped}


def _update_contact_outreach(contact_hash: str, campaign_id: str) -> None:
    """Update the master contacts list to reflect a send."""
    contacts = load_press_contacts()
    for c in contacts:
        if c["hash"] == contact_hash:
            c["last_contacted"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            c["outreach_count"] = c.get("outreach_count", 0) + 1
            if campaign_id not in c.get("campaigns", []):
                c.setdefault("campaigns", []).append(campaign_id)
            break
    save_press_contacts(contacts)


# ── Campaign queries ────────────────────────────────────────────────────

def list_campaigns() -> list[dict]:
    """List all campaigns (summary only)."""
    campaigns = []
    for p in sorted(_campaigns_dir().glob("*.json"), reverse=True):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            campaigns.append({
                "id": data["id"],
                "name": data["name"],
                "event_type": data["event_type"],
                "vertical": data["vertical"],
                "status": data["status"],
                "stats": data.get("stats", {}),
                "created_at": data["created_at"],
                "distributed_at": data.get("distributed_at"),
            })
        except Exception:
            continue
    return campaigns


def get_campaign(campaign_id: str) -> dict | None:
    """Get full campaign details."""
    return _load_campaign(campaign_id)


def update_campaign_press_release(campaign_id: str, press_release: dict) -> dict | None:
    """Update the press release content for a campaign (for manual editing)."""
    campaign = _load_campaign(campaign_id)
    if not campaign:
        return None
    campaign["press_release"] = press_release
    campaign["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _save_campaign(campaign)
    return campaign


def add_contacts_to_campaign(campaign_id: str, contact_hashes: list[str]) -> dict | None:
    """Add additional contacts to a campaign by their hash IDs."""
    campaign = _load_campaign(campaign_id)
    if not campaign:
        return None

    existing_hashes = {c["hash"] for c in campaign["contacts"]}
    all_contacts = load_press_contacts()
    contacts_by_hash = {c["hash"]: c for c in all_contacts}

    added = 0
    for h in contact_hashes:
        if h in existing_hashes:
            continue
        c = contacts_by_hash.get(h)
        if not c:
            continue
        campaign["contacts"].append({
            "hash": c["hash"],
            "name": c["name"],
            "email": c.get("email", ""),
            "type": c.get("type", ""),
            "send_status": "pending",
            "message_id": None,
            "sent_at": None,
        })
        existing_hashes.add(h)
        added += 1

    campaign["stats"]["total_contacts"] = len(campaign["contacts"])
    campaign["stats"]["with_email"] = sum(
        1 for c in campaign["contacts"] if c.get("email")
    )
    campaign["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _save_campaign(campaign)

    return campaign
