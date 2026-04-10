"""Brand profile loader — provides business context to the press system.

Reads brand_profile.json for verticals, tone, and discovery search terms.
Also scans store_items.json and track_memory for current releases.
"""

import json
import logging
from pathlib import Path

from app.core.config import get_settings

log = logging.getLogger(__name__)


def _press_dir() -> Path:
    d = Path(get_settings().exports_dir) / "press"
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_brand_profile() -> dict:
    """Load the brand profile, enriched with current releases from the store."""
    p = _press_dir() / "brand_profile.json"
    if not p.exists():
        log.warning("brand_profile.json not found — using defaults")
        return {"name": "NullRecords", "verticals": [], "tone": {}}

    profile = json.loads(p.read_text(encoding="utf-8"))

    # Enrich with current store releases
    store_path = Path(get_settings().exports_dir).parent.parent / "docs" / "store" / "store_items.json"
    if store_path.exists():
        try:
            items = json.loads(store_path.read_text(encoding="utf-8"))
            for vertical in profile.get("verticals", []):
                if vertical["id"] == "music":
                    vertical["releases"] = [
                        {"title": i["title"], "artist": i.get("artist", ""), "type": "album"}
                        for i in items if i.get("type") == "music" and i.get("active")
                    ]
                elif vertical["id"] == "books":
                    vertical["releases"] = [
                        {"title": i["title"], "author": i.get("author", ""), "type": "book"}
                        for i in items if i.get("type") == "book" and i.get("active")
                    ]
        except Exception:
            log.debug("Could not load store items for brand enrichment")

    return profile


def save_brand_profile(profile: dict) -> None:
    """Persist updated brand profile."""
    p = _press_dir() / "brand_profile.json"
    p.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")


def get_brand_summary(vertical_id: str | None = None) -> str:
    """Return a text summary of the brand for AI prompts."""
    profile = load_brand_profile()
    parts = [f"{profile['name']} — {profile.get('tagline', '')}"]
    parts.append(f"Website: {profile.get('website', '')}")

    verticals = profile.get("verticals", [])
    if vertical_id:
        verticals = [v for v in verticals if v["id"] == vertical_id]

    for v in verticals:
        parts.append(f"\n## {v['name']}")
        parts.append(v.get("description", ""))
        releases = v.get("releases", [])
        if releases:
            parts.append("Current releases:")
            for r in releases:
                label = r.get("artist") or r.get("author", "")
                parts.append(f"  - {r['title']} by {label}")

    tone = profile.get("tone", {})
    if tone.get("voice"):
        parts.append(f"\nBrand voice: {tone['voice']}")

    return "\n".join(parts)
