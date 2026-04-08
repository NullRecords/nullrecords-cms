"""YouTube upload service — OAuth2 + YouTube Data API v3.

Handles the full OAuth2 authorization code flow and video uploads.
Tokens are persisted to disk so re-auth is only needed once.
"""

import json
import logging
from pathlib import Path

import requests

from app.core.config import get_settings

log = logging.getLogger(__name__)

_TOKEN_FILE = Path(get_settings().exports_dir).parent / ".youtube_tokens.json"

SCOPES = "https://www.googleapis.com/auth/youtube.upload"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


def _load_tokens() -> dict | None:
    if _TOKEN_FILE.exists():
        return json.loads(_TOKEN_FILE.read_text())
    return None


def _save_tokens(tokens: dict) -> None:
    _TOKEN_FILE.write_text(json.dumps(tokens, indent=2))


def get_auth_url(redirect_uri: str) -> str:
    """Return the Google OAuth2 consent URL the user must visit."""
    settings = get_settings()
    client_id = settings.youtube_client_id
    if not client_id:
        raise ValueError("YOUTUBE_CLIENT_ID not configured in .env")

    return (
        f"{AUTH_URL}?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope={SCOPES}"
        f"&access_type=offline"
        f"&prompt=consent"
    )


def exchange_code(code: str, redirect_uri: str) -> dict:
    """Exchange an authorization code for access + refresh tokens."""
    settings = get_settings()
    resp = requests.post(TOKEN_URL, data={
        "code": code,
        "client_id": settings.youtube_client_id,
        "client_secret": settings.youtube_client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }, timeout=30)
    resp.raise_for_status()
    tokens = resp.json()
    _save_tokens(tokens)
    log.info("YouTube tokens saved successfully.")
    return tokens


def _get_access_token() -> str:
    """Get an access token — prefer OAuth refresh, fall back to API key."""
    tokens = _load_tokens()
    if tokens and "refresh_token" in tokens:
        return _refresh_oauth_token(tokens)
    # Fall back to API key
    settings = get_settings()
    if settings.youtube_api_key:
        return settings.youtube_api_key
    raise ValueError("No YouTube credentials. Set YOUTUBE_API_KEY or complete OAuth via /video/youtube/auth.")


def _refresh_oauth_token(tokens: dict) -> str:
    """Use the stored refresh token to get a fresh access token."""

    settings = get_settings()
    resp = requests.post(TOKEN_URL, data={
        "client_id": settings.youtube_client_id,
        "client_secret": settings.youtube_client_secret,
        "refresh_token": tokens["refresh_token"],
        "grant_type": "refresh_token",
    }, timeout=30)
    resp.raise_for_status()
    new_tokens = resp.json()
    # Preserve the refresh token (Google doesn't always re-issue it)
    new_tokens["refresh_token"] = tokens["refresh_token"]
    _save_tokens(new_tokens)
    return new_tokens["access_token"]


def is_authenticated() -> bool:
    """Check whether we can upload — either via stored OAuth tokens or API key."""
    tokens = _load_tokens()
    if tokens and tokens.get("refresh_token"):
        return True
    # API key alone counts as authenticated for upload
    settings = get_settings()
    return bool(settings.youtube_api_key)


def upload_video(
    video_path: str,
    title: str,
    description: str,
    tags: list[str],
    privacy: str = "public",
    category_id: str = "10",  # Music category
) -> dict:
    """Upload a video to YouTube.

    Returns dict with video id, url, and status.
    """
    access_token = _get_access_token()
    video = Path(video_path)
    if not video.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    metadata = {
        "snippet": {
            "title": title or video.stem,
            "description": description,
            "tags": tags,
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    # Resumable upload — initiate
    init_resp = requests.post(
        f"{UPLOAD_URL}?uploadType=resumable&part=snippet,status",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": "video/mp4",
            "X-Upload-Content-Length": str(video.stat().st_size),
        },
        json=metadata,
        timeout=30,
    )
    init_resp.raise_for_status()
    upload_uri = init_resp.headers["Location"]

    # Upload the video bytes
    with open(video, "rb") as f:
        upload_resp = requests.put(
            upload_uri,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "video/mp4",
            },
            data=f,
            timeout=600,
        )
    upload_resp.raise_for_status()
    result = upload_resp.json()

    video_id = result.get("id", "")
    log.info("YouTube upload complete: %s", video_id)

    return {
        "video_id": video_id,
        "url": f"https://www.youtube.com/watch?v={video_id}" if video_id else "",
        "status": result.get("status", {}).get("uploadStatus", "unknown"),
    }


def fetch_video_stats(video_ids: list[str]) -> dict[str, dict]:
    """Fetch statistics for one or more YouTube video IDs.

    Uses the API key (no OAuth needed for public video stats).
    Returns {video_id: {views, likes, comments, favorites}} for each found video.
    """
    settings = get_settings()
    api_key = settings.youtube_api_key
    if not api_key:
        log.warning("No YOUTUBE_API_KEY — cannot fetch stats")
        return {}

    stats = {}
    # API allows up to 50 IDs per request
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i : i + 50]
        try:
            resp = requests.get(
                VIDEOS_URL,
                params={
                    "part": "statistics,snippet",
                    "id": ",".join(batch),
                    "key": api_key,
                },
                timeout=15,
            )
            resp.raise_for_status()
            for item in resp.json().get("items", []):
                vid = item["id"]
                s = item.get("statistics", {})
                sn = item.get("snippet", {})
                stats[vid] = {
                    "views": int(s.get("viewCount", 0)),
                    "likes": int(s.get("likeCount", 0)),
                    "comments": int(s.get("commentCount", 0)),
                    "favorites": int(s.get("favoriteCount", 0)),
                    "title": sn.get("title", ""),
                    "published_at": sn.get("publishedAt", ""),
                }
        except Exception:
            log.exception("Failed to fetch YouTube stats for batch starting at %d", i)

    return stats
