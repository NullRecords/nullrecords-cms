"""Outreach API routes."""

import logging
import threading
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db, SessionLocal
from app.models.playlist import Playlist
from app.models.influencer import Influencer
from app.models.outreach import OutreachLog
from app.schemas.playlist import DiscoverRequest, InfluencerOut, PlaylistOut
from app.schemas.outreach import OutreachLogOut, OutreachSendRequest, BatchOutreachRequest, BatchOutreachResult
from app.services.outreach.discovery import discover_playlists, discover_influencers
from app.services.outreach.scoring import score_relevance
from app.services.outreach.messaging import generate_outreach_message, generate_outreach_subject
from app.services.outreach.followup import schedule_follow_up, get_pending_followups
from app.services.outreach.email_sender import send_email
from app.services.outreach.contact_finder import enrich_contact

logger = logging.getLogger(__name__)

# ── Background task status tracking ──────────────────────────────────────
_task_status: dict[str, dict] = {}
_task_lock = threading.Lock()


def _update_task(task_id: str, **kwargs):
    with _task_lock:
        if task_id not in _task_status:
            _task_status[task_id] = {}
        _task_status[task_id].update(kwargs)


router = APIRouter(prefix="/outreach", tags=["outreach"])


# ── Task status endpoint ─────────────────────────────────────────────────

@router.get("/task-status/{task_id}")
def get_task_status(task_id: str):
    with _task_lock:
        status = _task_status.get(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")
    return status


def _has_actionable_contact(contact: str) -> bool:
    """Check if a contact string is something we can actually send to (email or social DM)."""
    if not contact:
        return False
    # Email address
    if "@" in contact:
        return True
    # Social handle (instagram:@handle, twitter:@handle, etc.)
    if ":" in contact and any(p in contact.lower() for p in ["instagram", "twitter", "tiktok", "discord", "reddit_modmail"]):
        return True
    return False


@router.post("/discover", response_model=dict)
def discover(req: DiscoverRequest, db: Session = Depends(get_db)):
    """Discover playlists and influencers across public platforms, score them, and store in DB."""
    playlists_raw = discover_playlists(req.query)
    influencers_raw = discover_influencers(req.query)

    playlists_added = 0
    for p in playlists_raw:
        existing = db.query(Playlist).filter_by(name=p["name"], platform=p["platform"]).first()
        if existing:
            continue
        relevance = score_relevance(p["name"], p.get("curator_name", ""))
        pl = Playlist(
            name=p["name"],
            platform=p["platform"],
            curator_name=p.get("curator_name", ""),
            followers=p.get("followers", 0),
            contact=p.get("contact", ""),
            url=p.get("url", ""),
            relevance_score=relevance,
        )
        db.add(pl)
        playlists_added += 1

    influencers_added = 0
    for i in influencers_raw:
        existing = db.query(Influencer).filter_by(handle=i["handle"], platform=i["platform"]).first()
        if existing:
            continue
        relevance = score_relevance(i["handle"], i.get("niche", ""))
        inf = Influencer(
            handle=i["handle"],
            platform=i["platform"],
            followers=i.get("followers", 0),
            niche=i.get("niche", ""),
            contact=i.get("contact", ""),
            relevance_score=relevance,
        )
        db.add(inf)
        influencers_added += 1

    db.commit()
    return {
        "playlists_added": playlists_added,
        "influencers_added": influencers_added,
    }


def _build_target_context(target, target_type: str) -> str:
    """Build rich context string for AI message personalization."""
    if target_type == "playlist":
        parts = [f"{target.platform} playlist '{target.name}'"]
        if target.curator_name:
            parts.append(f"curated by {target.curator_name}")
        if target.followers:
            parts.append(f"{target.followers:,} followers")
        if target.url:
            parts.append(f"URL: {target.url}")
        return ", ".join(parts)
    else:
        parts = [f"{target.platform} creator @{target.handle}"]
        if target.niche:
            parts.append(f"niche: {target.niche}")
        if target.followers:
            parts.append(f"{target.followers:,} followers")
        if target.contact:
            parts.append(f"contact: {target.contact}")
        return ", ".join(parts)


@router.post("/generate/{target_type}/{target_id}")
def generate_message(target_type: str, target_id: int, db: Session = Depends(get_db)):
    """Generate an outreach message for a playlist or influencer."""
    if target_type == "playlist":
        target = db.query(Playlist).filter(Playlist.id == target_id).first()
        if not target:
            raise HTTPException(status_code=404, detail="Playlist not found")
        name = target.name
    elif target_type == "influencer":
        target = db.query(Influencer).filter(Influencer.id == target_id).first()
        if not target:
            raise HTTPException(status_code=404, detail="Influencer not found")
        name = target.handle
    else:
        raise HTTPException(status_code=400, detail="target_type must be 'playlist' or 'influencer'")

    context = _build_target_context(target, target_type)
    message = generate_outreach_message(name, target_type, context)
    subject = generate_outreach_subject(name, target_type, context)
    return {"target_type": target_type, "target_id": target_id, "message": message, "subject": subject}


@router.post("/send", response_model=OutreachLogOut)
def send_outreach(req: OutreachSendRequest, request: Request, db: Session = Depends(get_db)):
    """Send an outreach message (email if contact available) and schedule a follow-up."""
    from app.core.config import get_settings
    settings = get_settings()

    # Look up target contact info
    contact = ""
    if req.target_type == "playlist":
        target = db.query(Playlist).filter(Playlist.id == req.target_id).first()
        name = target.name if target else ""
    else:
        target = db.query(Influencer).filter(Influencer.id == req.target_id).first()
        name = target.handle if target else ""
    if target:
        contact = target.contact or ""

    # Generate subject if not provided
    context = _build_target_context(target, req.target_type) if target else ""
    subject = f"Hello from {settings.label_name}"
    if target:
        subject = generate_outreach_subject(name, req.target_type, context)

    # Create log entry first so we have an ID for the tracking pixel
    log = OutreachLog(
        target_type=req.target_type,
        target_id=req.target_id,
        subject=subject,
        message=req.message,
        status="pending",
    )
    db.add(log)
    db.flush()

    # Validate contact before sending
    if not _has_actionable_contact(contact):
        log.status = "no_contact"
        db.commit()
        db.refresh(log)
        raise HTTPException(
            status_code=422,
            detail=f"No actionable contact for this target. Run /outreach/enrich-contacts first. Current contact: '{contact}'"
        )

    # Attempt email delivery if contact is an email address
    result = {"sent": False, "message_id": None, "method": "none"}
    if contact and "@" in contact:
        # Build tracking pixel URL
        base_url = str(request.base_url).rstrip("/")
        tracking_url = f"{base_url}/tracking/open/{log.id}.png"

        result = send_email(contact, subject, req.message, tracking_pixel_url=tracking_url)

    log.status = "sent" if result["sent"] else "logged"
    if result.get("message_id"):
        log.message_id = result["message_id"]
    if result["sent"]:
        log.delivered_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(log)

    # Mark the target as contacted
    if target:
        target.last_contacted = datetime.now(timezone.utc)
        db.commit()

    # Auto-schedule follow-up in 5 days
    schedule_follow_up(db, log.id, days=5)

    db.refresh(log)
    return log


@router.post("/batch-send", response_model=BatchOutreachResult)
def batch_send(req: BatchOutreachRequest, request: Request, db: Session = Depends(get_db)):
    """Send outreach to multiple targets at once. Generates messages and attempts delivery."""
    from app.core.config import get_settings
    settings = get_settings()
    base_url = str(request.base_url).rstrip("/")

    sent_count = 0
    logged_count = 0

    for item in req.targets:
        # Look up target
        if item.target_type == "playlist":
            target = db.query(Playlist).filter(Playlist.id == item.target_id).first()
            name = target.name if target else f"playlist-{item.target_id}"
            contact = (target.contact if target else "") or ""
        else:
            target = db.query(Influencer).filter(Influencer.id == item.target_id).first()
            name = target.handle if target else f"influencer-{item.target_id}"
            contact = (target.contact if target else "") or ""

        if not target:
            logged_count += 1
            continue

        # Skip targets without actionable contact
        if not _has_actionable_contact(contact):
            logged_count += 1
            continue

        context = _build_target_context(target, item.target_type)

        # Generate or use provided message
        message = item.message or generate_outreach_message(name, item.target_type, context)
        subject = generate_outreach_subject(name, item.target_type, context)

        # Create log entry
        log = OutreachLog(
            target_type=item.target_type,
            target_id=item.target_id,
            subject=subject,
            message=message,
            status="pending",
        )
        db.add(log)
        db.flush()

        # Attempt delivery
        result = {"sent": False, "message_id": None, "method": "none"}
        if contact and "@" in contact:
            tracking_url = f"{base_url}/tracking/open/{log.id}.png"
            result = send_email(contact, subject, message, tracking_pixel_url=tracking_url)

        log.status = "sent" if result["sent"] else "logged"
        if result.get("message_id"):
            log.message_id = result["message_id"]
        if result["sent"]:
            log.delivered_at = datetime.now(timezone.utc)

        if target:
            target.last_contacted = datetime.now(timezone.utc)

        schedule_follow_up(db, log.id, days=5)

        if result["sent"]:
            sent_count += 1
        else:
            logged_count += 1

    db.commit()
    return BatchOutreachResult(
        total=len(req.targets),
        sent=sent_count,
        logged=logged_count,
    )


@router.get("/followups", response_model=list[OutreachLogOut])
def followups(db: Session = Depends(get_db)):
    """Return all outreach entries due for follow-up."""
    return get_pending_followups(db)


@router.get("/playlists", response_model=list[PlaylistOut])
def list_playlists(db: Session = Depends(get_db)):
    """List all discovered playlists."""
    return db.query(Playlist).order_by(Playlist.relevance_score.desc()).all()


@router.get("/influencers", response_model=list[InfluencerOut])
def list_influencers(db: Session = Depends(get_db)):
    """List all discovered influencers."""
    return db.query(Influencer).order_by(Influencer.relevance_score.desc()).all()


@router.post("/enrich-contacts", response_model=dict)
def enrich_contacts(db: Session = Depends(get_db)):
    """Scrape web pages to find email addresses and social handles for all targets missing contacts."""
    enriched = 0
    skipped = 0
    errors = 0

    # Enrich playlists
    playlists = db.query(Playlist).all()
    for p in playlists:
        if _has_actionable_contact(p.contact):
            skipped += 1
            continue
        if not p.url:
            skipped += 1
            continue
        try:
            new_contact = enrich_contact(p.contact, p.url)
            if new_contact and new_contact != p.contact:
                p.contact = new_contact
                enriched += 1
            else:
                skipped += 1
        except Exception as exc:
            logger.warning("Failed to enrich playlist %s: %s", p.name, exc)
            errors += 1

    # Enrich influencers
    influencers = db.query(Influencer).all()
    for i in influencers:
        if _has_actionable_contact(i.contact):
            skipped += 1
            continue
        url = i.contact if i.contact and i.contact.startswith("http") else ""
        if not url:
            skipped += 1
            continue
        try:
            new_contact = enrich_contact("", url)
            if new_contact and new_contact != i.contact:
                i.contact = new_contact
                enriched += 1
            else:
                skipped += 1
        except Exception as exc:
            logger.warning("Failed to enrich influencer %s: %s", i.handle, exc)
            errors += 1

    db.commit()
    return {"enriched": enriched, "skipped": skipped, "errors": errors}


@router.post("/enrich-single/{target_type}/{target_id}", response_model=dict)
def enrich_single(target_type: str, target_id: int, db: Session = Depends(get_db)):
    """Enrich contact info for a single target."""
    if target_type == "playlist":
        target = db.query(Playlist).filter(Playlist.id == target_id).first()
        url = target.url if target else ""
        current = target.contact if target else ""
    elif target_type == "influencer":
        target = db.query(Influencer).filter(Influencer.id == target_id).first()
        url = target.contact if target and target.contact and target.contact.startswith("http") else ""
        current = target.contact if target else ""
    else:
        raise HTTPException(status_code=400, detail="target_type must be 'playlist' or 'influencer'")

    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    if not url:
        return {"status": "no_url", "contact": current}

    new_contact = enrich_contact(current if "@" in (current or "") else "", url)
    if new_contact and new_contact != current:
        target.contact = new_contact
        db.commit()
        return {"status": "enriched", "old_contact": current, "new_contact": new_contact}

    return {"status": "unchanged", "contact": current}


# ── News search (background) ─────────────────────────────────────────────

def _run_news_search(task_id: str):
    """Background worker for news search."""
    import json
    from pathlib import Path
    from app.core.config import get_settings
    from app.services.outreach.news_search import search_news

    try:
        _update_task(task_id, status="running", stage="searching")
        settings = get_settings()
        results = search_news(youtube_api_key=settings.youtube_api_key)
        _update_task(task_id, stage="merging", searched=len(results))

        workspace = Path(__file__).resolve().parents[3]
        news_file = workspace / "docs" / "news_articles.json"
        try:
            existing = json.loads(news_file.read_text()) if news_file.exists() else []
        except (json.JSONDecodeError, OSError):
            existing = []

        existing_urls = {a.get("url", "") for a in existing}
        new_count = 0
        for r in results:
            if r["url"] in existing_urls:
                continue
            existing.append(r)
            existing_urls.add(r["url"])
            new_count += 1

        if new_count > 0:
            news_file.write_text(json.dumps(existing, indent=2, default=str))

        _update_task(task_id, status="completed", searched=len(results),
                     new_articles=new_count, total_articles=len(existing),
                     sources=list({r.get("source", "unknown").split("/")[0] for r in results}))
    except Exception as e:
        logger.error("News search failed: %s", e)
        _update_task(task_id, status="failed", error=str(e))


@router.post("/news-search", response_model=dict)
def news_search(background_tasks: BackgroundTasks):
    """Search the web for mentions of NullRecords and My Evil Robot Army.

    Returns immediately with a task_id. Poll /outreach/task-status/{task_id} for results.
    """
    task_id = f"news_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    _update_task(task_id, status="queued", started_at=datetime.now(timezone.utc).isoformat())
    background_tasks.add_task(_run_news_search, task_id)
    return {"task_id": task_id, "status": "queued", "poll_url": f"/outreach/task-status/{task_id}"}


# ── DJ & radio station discovery (background) ────────────────────────────

def _run_dj_radio_discovery(task_id: str):
    """Background worker for DJ/radio discovery."""
    from app.services.outreach.dj_radio_discovery import discover_dj_radio
    from app.services.outreach.scoring import score_relevance

    try:
        _update_task(task_id, status="running", stage="searching")
        raw = discover_dj_radio()
        _update_task(task_id, stage="storing", discovered=len(raw))

        db = SessionLocal()
        try:
            added = 0
            skipped = 0
            by_scope = {"local": 0, "national": 0, "international": 0}
            by_category = {}

            for r in raw:
                existing = db.query(Influencer).filter_by(
                    handle=r["handle"], platform=r["platform"]
                ).first()
                if existing:
                    skipped += 1
                    continue

                relevance = score_relevance(r["handle"], r.get("niche", ""))
                inf = Influencer(
                    handle=r["handle"],
                    platform=r["platform"],
                    followers=r.get("followers", 0),
                    niche=r.get("niche", ""),
                    contact=r.get("contact", ""),
                    relevance_score=relevance,
                )
                db.add(inf)
                added += 1

                scope = r.get("scope", "national")
                by_scope[scope] = by_scope.get(scope, 0) + 1
                cat = r.get("category", "unknown")
                by_category[cat] = by_category.get(cat, 0) + 1

            db.commit()
            _update_task(task_id, status="completed", discovered=len(raw),
                         added=added, skipped_existing=skipped,
                         by_scope=by_scope, by_category=by_category)
        finally:
            db.close()
    except Exception as e:
        logger.error("DJ/Radio discovery failed: %s", e)
        _update_task(task_id, status="failed", error=str(e))


@router.post("/discover-dj-radio", response_model=dict)
def discover_dj_radio_endpoint(background_tasks: BackgroundTasks):
    """Discover DJs, radio stations, and music shows (local, national, international).

    Returns immediately with a task_id. Poll /outreach/task-status/{task_id} for results.
    """
    task_id = f"djradio_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    _update_task(task_id, status="queued", started_at=datetime.now(timezone.utc).isoformat())
    background_tasks.add_task(_run_dj_radio_discovery, task_id)
    return {"task_id": task_id, "status": "queued", "poll_url": f"/outreach/task-status/{task_id}"}
