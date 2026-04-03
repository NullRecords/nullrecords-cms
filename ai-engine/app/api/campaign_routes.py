"""Campaign API — dynamic access to pre-save and release campaigns."""

import json
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/campaign", tags=["campaign"])

STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
CAMPAIGN_FILE = STATIC_DIR / "presave_campaign.json"


def _load_campaign() -> dict:
    """Load the campaign JSON."""
    if not CAMPAIGN_FILE.exists():
        raise HTTPException(status_code=404, detail="No campaign file found")
    with open(CAMPAIGN_FILE) as f:
        return json.load(f)


def _save_campaign(data: dict):
    """Write campaign JSON back to disk."""
    with open(CAMPAIGN_FILE, "w") as f:
        json.dump(data, f, indent=2)


@router.get("")
def get_campaign():
    """Full campaign data with post status tracking."""
    data = _load_campaign()
    today = date.today().isoformat()

    for post in data.get("daily_posts", []):
        post_date = post.get("day", "")
        if post_date < today:
            post.setdefault("status", "past")
        elif post_date == today:
            post.setdefault("status", "today")
        else:
            post.setdefault("status", "upcoming")

    return data


@router.get("/today")
def get_today_posts():
    """Get today's social media posts — the one endpoint you need each morning."""
    data = _load_campaign()
    today = date.today().isoformat()

    for post in data.get("daily_posts", []):
        if post.get("day") == today:
            return {
                "campaign": data.get("campaign"),
                "artist": data.get("artist"),
                "presave_url": data.get("presave_url"),
                "date": today,
                "days_until": post.get("days_until"),
                "theme": post.get("theme"),
                "platforms": {
                    k: v for k, v in post.items()
                    if k not in ("day", "days_until", "theme", "status", "posted")
                },
                "posted": post.get("posted", {}),
            }

    return {
        "date": today,
        "message": "No campaign posts scheduled for today",
        "campaign": data.get("campaign"),
    }


@router.post("/today/{platform}/posted")
def mark_posted(platform: str):
    """Mark a platform's post as done for today."""
    data = _load_campaign()
    today = date.today().isoformat()
    valid_platforms = {"tiktok", "instagram", "youtube", "twitter_x"}

    if platform not in valid_platforms:
        raise HTTPException(status_code=400, detail=f"Unknown platform. Use: {', '.join(valid_platforms)}")

    for post in data.get("daily_posts", []):
        if post.get("day") == today:
            posted = post.setdefault("posted", {})
            posted[platform] = datetime.now().isoformat()
            _save_campaign(data)
            return {"status": "ok", "platform": platform, "marked_at": posted[platform]}

    raise HTTPException(status_code=404, detail="No campaign post for today")


@router.get("/status")
def campaign_status():
    """Quick overview — what's posted, what's pending."""
    data = _load_campaign()
    today = date.today().isoformat()
    platforms = ["tiktok", "instagram", "youtube", "twitter_x"]

    summary = {
        "campaign": data.get("campaign"),
        "release_date": data.get("release_date"),
        "today": today,
        "days": [],
    }

    for post in data.get("daily_posts", []):
        day = post.get("day", "")
        posted = post.get("posted", {})
        day_info = {
            "date": day,
            "theme": post.get("theme"),
            "is_today": day == today,
            "platforms": {
                p: {"has_content": p in post, "posted": posted.get(p)}
                for p in platforms
            },
        }
        summary["days"].append(day_info)

    return summary
