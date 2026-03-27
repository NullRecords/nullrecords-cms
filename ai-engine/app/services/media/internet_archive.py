"""Internet Archive video search plugin (public domain, no key required)."""

import logging
from typing import Any

import requests

from app.services.media.base import MediaSource

log = logging.getLogger(__name__)

VIDEO_EXTENSIONS = (".mp4", ".ogv", ".webm", ".avi", ".mov", ".mkv")


class InternetArchiveSource(MediaSource):
    source_name = "internet_archive"

    SEARCH_URL = "https://archive.org/advancedsearch.php"
    METADATA_URL = "https://archive.org/metadata"
    DOWNLOAD_URL = "https://archive.org/download"

    def search(self, query: str, per_page: int = 10) -> list[dict[str, Any]]:
        params = {
            "q": f"{query} AND mediatype:movies",
            "fl[]": ["identifier", "title", "description", "avg_rating"],
            "rows": per_page,
            "page": 1,
            "output": "json",
        }
        resp = requests.get(self.SEARCH_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", {}).get("docs", [])

    def normalize(self, result: dict[str, Any]) -> dict[str, Any]:
        identifier = result.get("identifier", "")
        title = result.get("title", identifier)

        # Resolve a direct video file download URL via the metadata API
        download_url = self._resolve_video_url(identifier)

        return {
            "source": self.source_name,
            "source_id": identifier,
            "title": title,
            "url": download_url,
            "preview_url": f"https://archive.org/services/img/{identifier}",
            "duration": 0.0,
        }

    def _resolve_video_url(self, identifier: str) -> str:
        """Query IA metadata to find the best downloadable video file URL."""
        try:
            resp = requests.get(
                f"{self.METADATA_URL}/{identifier}/files",
                timeout=15,
            )
            resp.raise_for_status()
            files = resp.json().get("result", [])
        except Exception as exc:
            log.warning("Failed to fetch IA metadata for %s: %s", identifier, exc)
            return f"{self.DOWNLOAD_URL}/{identifier}"

        # Prefer mp4, then other video formats, sorted by size descending
        video_files = [
            f for f in files
            if f.get("name", "").lower().endswith(VIDEO_EXTENSIONS)
        ]

        if not video_files:
            # Fallback: return the item download page (user can pick manually)
            log.warning("No video files found in IA item %s", identifier)
            return f"{self.DOWNLOAD_URL}/{identifier}"

        # Prefer mp4, then sort by file size (largest = highest quality)
        def _sort_key(f: dict) -> tuple:
            name = f.get("name", "").lower()
            is_mp4 = name.endswith(".mp4")
            size = int(f.get("size", 0))
            return (is_mp4, size)

        best = max(video_files, key=_sort_key)
        url = f"{self.DOWNLOAD_URL}/{identifier}/{best['name']}"
        log.info("Resolved IA video URL: %s", url)
        return url
