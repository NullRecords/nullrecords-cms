"""Internet Archive video search plugin (public domain, no key required)."""

from typing import Any

import requests

from app.services.media.base import MediaSource


class InternetArchiveSource(MediaSource):
    source_name = "internet_archive"

    SEARCH_URL = "https://archive.org/advancedsearch.php"

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
        return {
            "source": self.source_name,
            "source_id": identifier,
            "title": title,
            "url": f"https://archive.org/details/{identifier}",
            "preview_url": f"https://archive.org/services/img/{identifier}",
            "duration": 0.0,  # IA advanced search doesn't return duration
        }
