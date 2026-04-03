"""Pexels video search plugin."""

import logging
from typing import Any

import requests

from app.core.config import get_settings
from app.services.media.base import MediaSource

logger = logging.getLogger(__name__)


class PexelsSource(MediaSource):
    source_name = "pexels"

    API_BASE = "https://api.pexels.com/videos/search"

    def _get_api_key(self) -> str | None:
        return get_settings().pexels_api_key or None

    def search(self, query: str, per_page: int = 10) -> list[dict[str, Any]]:
        api_key = self._get_api_key()
        if not api_key:
            logger.warning("Pexels API key not configured — skipping Pexels search")
            return []
        resp = requests.get(
            self.API_BASE,
            headers={"Authorization": api_key},
            params={"query": query, "per_page": per_page},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("videos", [])

    def normalize(self, result: dict[str, Any]) -> dict[str, Any]:
        video_files = result.get("video_files", [])
        # Pick the first HD file, or fall back to the first file available
        best = next(
            (f for f in video_files if f.get("quality") == "hd"),
            video_files[0] if video_files else {},
        )
        preview_pics = result.get("video_pictures", [])
        preview_url = preview_pics[0]["picture"] if preview_pics else ""

        return {
            "source": self.source_name,
            "source_id": str(result["id"]),
            "title": result.get("url", "").split("/")[-1].replace("-", " ").title()
                     if result.get("url") else f"Pexels {result['id']}",
            "url": best.get("link", ""),
            "preview_url": preview_url,
            "duration": float(result.get("duration", 0)),
        }
