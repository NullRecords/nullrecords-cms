"""Outreach API routes."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.playlist import Playlist
from app.models.influencer import Influencer
from app.models.outreach import OutreachLog
from app.schemas.playlist import DiscoverRequest, InfluencerOut, PlaylistOut
from app.schemas.outreach import OutreachLogOut, OutreachSendRequest
from app.services.outreach.discovery import discover_spotify_playlists, discover_youtube_channels
from app.services.outreach.scoring import score_relevance
from app.services.outreach.messaging import generate_outreach_message
from app.services.outreach.followup import schedule_follow_up, get_pending_followups

router = APIRouter(prefix="/outreach", tags=["outreach"])


@router.post("/discover", response_model=dict)
def discover(req: DiscoverRequest, db: Session = Depends(get_db)):
    """Discover playlists and influencers, score them, and store in DB."""
    playlists_raw = discover_spotify_playlists(req.query)
    influencers_raw = discover_youtube_channels(req.query)

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


@router.post("/generate/{target_type}/{target_id}")
def generate_message(target_type: str, target_id: int, db: Session = Depends(get_db)):
    """Generate an outreach message for a playlist or influencer."""
    if target_type == "playlist":
        target = db.query(Playlist).filter(Playlist.id == target_id).first()
        if not target:
            raise HTTPException(status_code=404, detail="Playlist not found")
        name = target.name
        context = f"Spotify playlist with {target.followers} followers, curated by {target.curator_name}"
    elif target_type == "influencer":
        target = db.query(Influencer).filter(Influencer.id == target_id).first()
        if not target:
            raise HTTPException(status_code=404, detail="Influencer not found")
        name = target.handle
        context = f"{target.platform} creator in {target.niche} with {target.followers} followers"
    else:
        raise HTTPException(status_code=400, detail="target_type must be 'playlist' or 'influencer'")

    message = generate_outreach_message(name, target_type, context)
    return {"target_type": target_type, "target_id": target_id, "message": message}


@router.post("/send", response_model=OutreachLogOut)
def send_outreach(req: OutreachSendRequest, db: Session = Depends(get_db)):
    """Log an outreach message (mock send) and schedule a follow-up."""
    log = OutreachLog(
        target_type=req.target_type,
        target_id=req.target_id,
        message=req.message,
        status="sent",
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    # Mark the target as contacted
    if req.target_type == "playlist":
        target = db.query(Playlist).filter(Playlist.id == req.target_id).first()
    else:
        target = db.query(Influencer).filter(Influencer.id == req.target_id).first()
    if target:
        target.last_contacted = datetime.now(timezone.utc)
        db.commit()

    # Auto-schedule follow-up in 5 days
    schedule_follow_up(db, log.id, days=5)

    db.refresh(log)
    return log


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
