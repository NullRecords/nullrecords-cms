"""Admin API routes — powers the web-based admin dashboard."""

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.media import MediaAsset
from app.models.playlist import Playlist
from app.models.influencer import Influencer
from app.models.outreach import OutreachLog
from app.models.credentials import APICredential

router = APIRouter(prefix="/admin/api", tags=["admin"])


@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    """Aggregate counts and recent activity for the dashboard overview."""
    settings = get_settings()

    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    media_total = db.query(func.count(MediaAsset.id)).scalar() or 0
    media_downloaded = db.query(func.count(MediaAsset.id)).filter(MediaAsset.downloaded.is_(True)).scalar() or 0
    media_tagged = db.query(func.count(MediaAsset.id)).filter(MediaAsset.mood != "", MediaAsset.mood.isnot(None)).scalar() or 0

    playlists_total = db.query(func.count(Playlist.id)).scalar() or 0
    influencers_total = db.query(func.count(Influencer.id)).scalar() or 0

    outreach_total = db.query(func.count(OutreachLog.id)).scalar() or 0
    outreach_sent = db.query(func.count(OutreachLog.id)).filter(OutreachLog.status == "sent").scalar() or 0
    outreach_pending = db.query(func.count(OutreachLog.id)).filter(
        OutreachLog.follow_up_date.isnot(None),
        OutreachLog.follow_up_date <= now,
        OutreachLog.status != "followed_up",
    ).scalar() or 0

    creds = db.query(APICredential.service).all()
    configured_services = [c.service for c in creds]

    # Config status
    api_status = {
        "openai": bool(settings.openai_api_key),
        "pexels": bool(settings.pexels_api_key),
        "spotify": bool(settings.spotify_client_id and settings.spotify_client_secret),
        "youtube": bool(settings.youtube_api_key),
    }

    return {
        "media": {"total": media_total, "downloaded": media_downloaded, "tagged": media_tagged},
        "outreach": {
            "playlists": playlists_total,
            "influencers": influencers_total,
            "messages_sent": outreach_sent,
            "followups_due": outreach_pending,
            "total_logs": outreach_total,
        },
        "api_status": api_status,
        "configured_services": configured_services,
        "label": {"name": settings.label_name, "genre": settings.label_genre},
    }


@router.get("/media")
def list_media(limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    """Paginated media asset list."""
    total = db.query(func.count(MediaAsset.id)).scalar() or 0
    items = (
        db.query(MediaAsset)
        .order_by(MediaAsset.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "total": total,
        "items": [
            {
                "id": m.id,
                "source": m.source,
                "title": m.title,
                "url": m.url,
                "tags": m.tags,
                "mood": m.mood,
                "style": m.style,
                "downloaded": m.downloaded,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in items
        ],
    }


@router.get("/playlists")
def list_playlists(limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    """Paginated playlist list."""
    total = db.query(func.count(Playlist.id)).scalar() or 0
    items = (
        db.query(Playlist)
        .order_by(Playlist.relevance_score.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "total": total,
        "items": [
            {
                "id": p.id,
                "name": p.name,
                "platform": p.platform,
                "curator_name": p.curator_name,
                "followers": p.followers,
                "url": p.url,
                "relevance_score": p.relevance_score,
                "last_contacted": p.last_contacted.isoformat() if p.last_contacted else None,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in items
        ],
    }


@router.get("/influencers")
def list_influencers(limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    """Paginated influencer list."""
    total = db.query(func.count(Influencer.id)).scalar() or 0
    items = (
        db.query(Influencer)
        .order_by(Influencer.relevance_score.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "total": total,
        "items": [
            {
                "id": i.id,
                "handle": i.handle,
                "platform": i.platform,
                "followers": i.followers,
                "niche": i.niche,
                "relevance_score": i.relevance_score,
                "last_contacted": i.last_contacted.isoformat() if i.last_contacted else None,
                "created_at": i.created_at.isoformat() if i.created_at else None,
            }
            for i in items
        ],
    }


@router.get("/outreach-log")
def outreach_log(limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    """Paginated outreach log."""
    total = db.query(func.count(OutreachLog.id)).scalar() or 0
    items = (
        db.query(OutreachLog)
        .order_by(OutreachLog.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "total": total,
        "items": [
            {
                "id": o.id,
                "target_type": o.target_type,
                "target_id": o.target_id,
                "message": o.message[:200] if o.message else "",
                "status": o.status,
                "follow_up_date": o.follow_up_date.isoformat() if o.follow_up_date else None,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o in items
        ],
    }


@router.get("/reports/summary")
def report_summary(db: Session = Depends(get_db)):
    """Generate an on-the-fly summary report of all AI Engine activity."""
    settings = get_settings()
    now = datetime.now(timezone.utc)

    # Media stats
    media_total = db.query(func.count(MediaAsset.id)).scalar() or 0
    media_by_source = (
        db.query(MediaAsset.source, func.count(MediaAsset.id))
        .group_by(MediaAsset.source)
        .all()
    )

    # Outreach stats
    outreach_by_status = (
        db.query(OutreachLog.status, func.count(OutreachLog.id))
        .group_by(OutreachLog.status)
        .all()
    )
    playlists_by_platform = (
        db.query(Playlist.platform, func.count(Playlist.id))
        .group_by(Playlist.platform)
        .all()
    )

    # Top playlists
    top_playlists = (
        db.query(Playlist)
        .order_by(Playlist.relevance_score.desc())
        .limit(5)
        .all()
    )

    # Top influencers
    top_influencers = (
        db.query(Influencer)
        .order_by(Influencer.relevance_score.desc())
        .limit(5)
        .all()
    )

    # Recent activity (last 7 days)
    week_ago = now - timedelta(days=7)
    recent_outreach = db.query(func.count(OutreachLog.id)).filter(
        OutreachLog.created_at >= week_ago
    ).scalar() or 0
    recent_media = db.query(func.count(MediaAsset.id)).filter(
        MediaAsset.created_at >= week_ago
    ).scalar() or 0

    return {
        "generated_at": now.isoformat(),
        "label": {"name": settings.label_name, "genre": settings.label_genre},
        "media": {
            "total": media_total,
            "by_source": {s: c for s, c in media_by_source},
            "added_last_7d": recent_media,
        },
        "outreach": {
            "by_status": {s: c for s, c in outreach_by_status},
            "sent_last_7d": recent_outreach,
            "playlists_by_platform": {p: c for p, c in playlists_by_platform},
            "top_playlists": [
                {"name": p.name, "platform": p.platform, "score": p.relevance_score}
                for p in top_playlists
            ],
            "top_influencers": [
                {"handle": i.handle, "platform": i.platform, "score": i.relevance_score}
                for i in top_influencers
            ],
        },
    }
