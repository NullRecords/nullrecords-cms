"""Playlist & influencer discovery.

Returns real data from configured APIs, or empty lists when APIs are unavailable.
"""

import logging
from typing import Any

import requests

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def discover_spotify_playlists(query: str) -> list[dict[str, Any]]:
    """Search Spotify for playlists matching *query*.

    Requires SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in .env.
    Returns an empty list when credentials are missing or the API call fails.
    """
    settings = get_settings()
    client_id = getattr(settings, "spotify_client_id", "")
    client_secret = getattr(settings, "spotify_client_secret", "")

    if not client_id or not client_secret:
        logger.info("Spotify credentials not configured — skipping playlist discovery")
        return []

    try:
        # Obtain bearer token via client-credentials flow
        token_resp = requests.post(
            "https://accounts.spotify.com/api/token",
            data={"grant_type": "client_credentials"},
            auth=(client_id, client_secret),
            timeout=10,
        )
        token_resp.raise_for_status()
        access_token = token_resp.json()["access_token"]

        # Search for playlists
        search_resp = requests.get(
            "https://api.spotify.com/v1/search",
            params={"q": query, "type": "playlist", "limit": 10},
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=15,
        )
        search_resp.raise_for_status()
        items = search_resp.json().get("playlists", {}).get("items", [])

        results: list[dict[str, Any]] = []
        for item in items:
            if not item:
                continue
            owner = item.get("owner", {}) or {}
            results.append({
                "name": item.get("name", ""),
                "platform": "spotify",
                "curator_name": owner.get("display_name", ""),
                "followers": (item.get("tracks", {}) or {}).get("total", 0),
                "contact": "",
                "url": (item.get("external_urls", {}) or {}).get("spotify", ""),
            })
        return results

    except Exception as exc:
        logger.warning("Spotify playlist discovery failed: %s", exc)
        return []


def discover_youtube_channels(query: str) -> list[dict[str, Any]]:
    """Search YouTube for channels matching *query*.

    Requires YOUTUBE_API_KEY in .env.
    Returns an empty list when the key is missing or the API call fails.
    """
    settings = get_settings()
    api_key = getattr(settings, "youtube_api_key", "")

    if not api_key:
        logger.info("YouTube API key not configured — skipping channel discovery")
        return []

    try:
        resp = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "q": query,
                "type": "channel",
                "part": "snippet",
                "maxResults": 10,
                "key": api_key,
            },
            timeout=15,
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])

        # Batch-fetch subscriber counts
        channel_ids = [it["snippet"]["channelId"] for it in items if it.get("snippet", {}).get("channelId")]
        stats_map: dict[str, int] = {}
        if channel_ids:
            stats_resp = requests.get(
                "https://www.googleapis.com/youtube/v3/channels",
                params={
                    "id": ",".join(channel_ids),
                    "part": "statistics",
                    "key": api_key,
                },
                timeout=15,
            )
            if stats_resp.ok:
                for ch in stats_resp.json().get("items", []):
                    stats_map[ch["id"]] = int(ch.get("statistics", {}).get("subscriberCount", 0))

        results: list[dict[str, Any]] = []
        for item in items:
            snippet = item.get("snippet", {})
            cid = snippet.get("channelId", "")
            results.append({
                "handle": snippet.get("channelTitle", ""),
                "platform": "youtube",
                "followers": stats_map.get(cid, 0),
                "niche": snippet.get("description", "")[:120],
                "contact": "",
            })
        return results

    except Exception as exc:
        logger.warning("YouTube channel discovery failed: %s", exc)
        return []
