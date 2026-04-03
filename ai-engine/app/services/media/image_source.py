"""Image sourcing — fetch stock images from Pexels or download from URL.

Provides high-quality still images that the renderer converts into
animated video clips via Ken Burns pan/zoom effects.
"""

import logging
import uuid
from pathlib import Path
from urllib.parse import urlparse

import requests

from app.core.config import get_settings

log = logging.getLogger(__name__)

_PEXELS_API = "https://api.pexels.com/v1/search"
_ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def _images_dir() -> Path:
    """Return (and create) the images directory inside media-library."""
    d = Path(get_settings().media_library_dir) / "images"
    d.mkdir(parents=True, exist_ok=True)
    return d


def search_pexels_images(query: str, count: int = 5) -> list[dict]:
    """Search Pexels for stock photos matching *query*.

    Returns a list of dicts with keys: url, preview_url, source_id, title, width, height.
    """
    api_key = get_settings().pexels_api_key
    if not api_key:
        log.warning("Pexels API key not configured — skipping image search")
        return []

    resp = requests.get(
        _PEXELS_API,
        headers={"Authorization": api_key},
        params={"query": query, "per_page": min(count, 40)},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    results = []
    for photo in data.get("photos", [])[:count]:
        src = photo.get("src", {})
        results.append({
            "source_id": str(photo["id"]),
            "title": photo.get("alt", f"Pexels {photo['id']}"),
            "url": src.get("original", src.get("large2x", "")),
            "preview_url": src.get("medium", src.get("small", "")),
            "width": photo.get("width", 0),
            "height": photo.get("height", 0),
        })

    log.info("Pexels image search '%s' → %d results", query, len(results))
    return results


def download_image(url: str, filename: str | None = None) -> Path:
    """Download an image from a URL to the local images directory.

    Returns the absolute Path to the saved file.
    """
    parsed = urlparse(url)
    if not filename:
        ext = Path(parsed.path).suffix.lower()
        if ext not in _ALLOWED_IMAGE_EXT:
            ext = ".jpg"
        filename = f"{uuid.uuid4().hex[:10]}{ext}"

    dest = _images_dir() / filename
    if dest.exists():
        return dest

    resp = requests.get(url, stream=True, timeout=30)
    resp.raise_for_status()

    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    log.info("Image downloaded: %s → %s (%.1f KB)", url[:80], dest.name, dest.stat().st_size / 1024)
    return dest


def fetch_images_for_video(
    query: str | None = None,
    image_urls: list[str] | None = None,
    count: int = 3,
) -> list[Path]:
    """Fetch images for video generation — from Pexels search or direct URLs.

    Args:
        query: Pexels search term (e.g. "cyberpunk city", "abstract neon").
        image_urls: Direct image URLs to download.
        count: How many Pexels images to fetch if using query.

    Returns:
        List of local Paths to downloaded images.
    """
    paths: list[Path] = []

    # Download direct URLs first
    if image_urls:
        for url in image_urls:
            try:
                p = download_image(url)
                paths.append(p)
                log.info("  Image from URL: %s", p.name)
            except Exception as exc:
                log.warning("  Failed to download image %s: %s", url[:60], exc)

    # Then search Pexels if a query is provided and we need more
    if query:
        needed = max(0, count - len(paths))
        if needed > 0:
            try:
                results = search_pexels_images(query, count=needed)
                for r in results:
                    try:
                        p = download_image(r["url"], f"pexels_{r['source_id']}.jpg")
                        paths.append(p)
                    except Exception as exc:
                        log.warning("  Failed to download Pexels image %s: %s", r["source_id"], exc)
            except Exception as exc:
                log.warning("Pexels image search failed: %s", exc)

    log.info("Fetched %d images for video", len(paths))
    return paths
