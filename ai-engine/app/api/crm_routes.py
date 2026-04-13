"""CRM API routes — subscriber management, Brevo sync, and lead-magnet delivery."""

import logging
from datetime import datetime, timezone

import requests
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.subscriber import Subscriber
from app.schemas.subscriber import (
    BulkImportItem,
    BulkTagRequest,
    CRMStats,
    SubscribeRequest,
    SubscriberOut,
    SubscriberUpdate,
    UnsubscribeRequest,
)
from app.services.crm.brevo_contacts import send_lead_magnet_email, sync_contact_to_brevo

logger = logging.getLogger(__name__)

BREVO_CONTACTS_URL = "https://api.brevo.com/v3/contacts"

router = APIRouter(prefix="/crm", tags=["crm"])


# ── Public: Subscribe endpoint (called from the website) ───────────────

@router.post("/subscribe", response_model=SubscriberOut)
def subscribe(req: SubscribeRequest, db: Session = Depends(get_db)):
    """Add a new subscriber. Syncs to Brevo and sends the lead-magnet email."""
    email_lower = req.email.strip().lower()

    existing = db.query(Subscriber).filter(Subscriber.email == email_lower).first()
    if existing:
        if existing.status == "unsubscribed":
            # Re-subscribe
            existing.status = "active"
            existing.unsubscribed_at = None
            existing.source = req.source or existing.source
            db.commit()
            db.refresh(existing)
            logger.info("Re-subscribed: %s", email_lower)
            return existing
        # Already active — return existing (idempotent)
        return existing

    sub = Subscriber(
        email=email_lower,
        name=req.name,
        source=req.source,
        tags="lead-magnet",
        status="active",
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    logger.info("New subscriber: %s (source=%s)", email_lower, req.source)

    # Sync to Brevo (async-safe: fire-and-forget pattern in background would be better,
    # but for a low-volume indie label this is fine synchronously)
    brevo_id = sync_contact_to_brevo(email_lower, req.name, req.source)
    if brevo_id:
        sub.brevo_contact_id = brevo_id
        db.commit()

    # Send the lead-magnet email
    if send_lead_magnet_email(email_lower, req.name):
        sub.lead_magnet_sent = True
        db.commit()

    db.refresh(sub)
    return sub


# ── Public: Unsubscribe endpoint ───────────────────────────────────────

@router.post("/unsubscribe")
def unsubscribe(req: UnsubscribeRequest, db: Session = Depends(get_db)):
    """Mark a subscriber as unsubscribed."""
    email_lower = req.email.strip().lower()
    sub = db.query(Subscriber).filter(Subscriber.email == email_lower).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Email not found")
    sub.status = "unsubscribed"
    sub.unsubscribed_at = datetime.now(timezone.utc)
    db.commit()
    logger.info("Unsubscribed: %s", email_lower)
    return {"ok": True, "email": email_lower}


# ── Admin: List subscribers ────────────────────────────────────────────

@router.get("/subscribers", response_model=list[SubscriberOut])
def list_subscribers(
    status: str = "active",
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """List subscribers, filtered by status."""
    q = db.query(Subscriber)
    if status != "all":
        q = q.filter(Subscriber.status == status)
    return q.order_by(Subscriber.created_at.desc()).offset(offset).limit(limit).all()


# ── Admin: Get single subscriber ──────────────────────────────────────

@router.get("/subscribers/{subscriber_id}", response_model=SubscriberOut)
def get_subscriber(subscriber_id: int, db: Session = Depends(get_db)):
    sub = db.query(Subscriber).filter(Subscriber.id == subscriber_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    return sub


# ── Admin: Update subscriber ──────────────────────────────────────────

@router.patch("/subscribers/{subscriber_id}", response_model=SubscriberOut)
def update_subscriber(subscriber_id: int, req: SubscriberUpdate, db: Session = Depends(get_db)):
    sub = db.query(Subscriber).filter(Subscriber.id == subscriber_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    if req.name is not None:
        sub.name = req.name
    if req.tags is not None:
        sub.tags = req.tags
    if req.status is not None:
        sub.status = req.status
        if req.status == "unsubscribed":
            sub.unsubscribed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(sub)
    return sub


# ── Admin: Bulk tag ────────────────────────────────────────────────────

@router.post("/subscribers/bulk-tag")
def bulk_tag(req: BulkTagRequest, db: Session = Depends(get_db)):
    """Add a tag to a list of subscribers by email."""
    updated = 0
    for email in req.email_list:
        sub = db.query(Subscriber).filter(Subscriber.email == email.strip().lower()).first()
        if sub:
            existing_tags = set(t.strip() for t in sub.tags.split(",") if t.strip())
            existing_tags.add(req.tag)
            sub.tags = ",".join(sorted(existing_tags))
            updated += 1
    db.commit()
    return {"updated": updated, "tag": req.tag}


# ── Admin: CRM stats ──────────────────────────────────────────────────

@router.get("/stats", response_model=CRMStats)
def crm_stats(db: Session = Depends(get_db)):
    """Aggregate CRM statistics."""
    total = db.query(func.count(Subscriber.id)).scalar() or 0
    active = db.query(func.count(Subscriber.id)).filter(Subscriber.status == "active").scalar() or 0
    unsub = db.query(func.count(Subscriber.id)).filter(Subscriber.status == "unsubscribed").scalar() or 0
    bounced = db.query(func.count(Subscriber.id)).filter(Subscriber.status == "bounced").scalar() or 0
    lead_sent = db.query(func.count(Subscriber.id)).filter(Subscriber.lead_magnet_sent == True).scalar() or 0  # noqa: E712

    # Source breakdown
    source_rows = (
        db.query(Subscriber.source, func.count(Subscriber.id))
        .group_by(Subscriber.source)
        .all()
    )
    sources = {row[0] or "unknown": row[1] for row in source_rows}

    return CRMStats(
        total=total,
        active=active,
        unsubscribed=unsub,
        bounced=bounced,
        lead_magnet_sent=lead_sent,
        sources=sources,
    )


# ── Admin: Sync contacts FROM Brevo into local CRM ────────────────────

@router.post("/sync-from-brevo")
def sync_from_brevo(db: Session = Depends(get_db)):
    """Pull all contacts from Brevo and upsert into the local CRM database."""
    from app.core.config import get_settings

    settings = get_settings()
    if not settings.smtp_key:
        raise HTTPException(status_code=500, detail="Brevo API key not configured")

    headers = {
        "api-key": settings.smtp_key,
        "Accept": "application/json",
    }

    imported = 0
    skipped = 0
    offset = 0
    limit = 50

    while True:
        resp = requests.get(
            BREVO_CONTACTS_URL,
            headers=headers,
            params={"limit": limit, "offset": offset},
            timeout=15,
        )
        if resp.status_code != 200:
            logger.warning("Brevo list contacts failed: %s %s", resp.status_code, resp.text[:200])
            break

        data = resp.json()
        contacts = data.get("contacts", [])
        if not contacts:
            break

        for contact in contacts:
            email = contact.get("email", "").strip().lower()
            if not email:
                continue

            existing = db.query(Subscriber).filter(Subscriber.email == email).first()
            if existing:
                # Update brevo_contact_id if missing
                if not existing.brevo_contact_id and contact.get("id"):
                    existing.brevo_contact_id = str(contact["id"])
                skipped += 1
                continue

            attrs = contact.get("attributes", {})
            name_parts = [attrs.get("FIRSTNAME", ""), attrs.get("LASTNAME", "")]
            name = " ".join(p for p in name_parts if p).strip() or None

            sub = Subscriber(
                email=email,
                name=name,
                source=attrs.get("SOURCE", "brevo-sync"),
                tags="brevo-import",
                status="active",
                brevo_contact_id=str(contact.get("id", "")),
            )
            db.add(sub)
            imported += 1

        db.commit()
        offset += limit
        if offset >= data.get("count", 0):
            break

    logger.info("Brevo sync complete: %d imported, %d skipped (already in CRM)", imported, skipped)
    return {"imported": imported, "skipped": skipped}


# ── Admin: Bulk import from JSON ───────────────────────────────────────

@router.post("/import")
def bulk_import(items: list[BulkImportItem], db: Session = Depends(get_db)):
    """Import a list of emails into the CRM. Skips duplicates, syncs new ones to Brevo."""
    imported = 0
    skipped = 0

    for item in items:
        email_lower = item.email.strip().lower()
        existing = db.query(Subscriber).filter(Subscriber.email == email_lower).first()
        if existing:
            skipped += 1
            continue

        sub = Subscriber(
            email=email_lower,
            name=item.name,
            source=item.source,
            tags="import",
            status="active",
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)

        brevo_id = sync_contact_to_brevo(email_lower, item.name, item.source)
        if brevo_id:
            sub.brevo_contact_id = brevo_id
            db.commit()

        imported += 1

    logger.info("Bulk import complete: %d imported, %d skipped", imported, skipped)
    return {"imported": imported, "skipped": skipped}
