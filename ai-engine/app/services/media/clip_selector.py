"""Clip selector — picks video clips from the local media library.

Queries the SQLite database for downloaded media assets matching the
requested mood / tags, then resolves to local file paths.
"""

import json
import logging
import random
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.media import MediaAsset

log = logging.getLogger(__name__)

# Clip count bounds
MIN_CLIPS = 2
MAX_CLIPS = 5


def select_clips(
    db: Session,
    mood: str | None = None,
    tags: list[str] | None = None,
    count: int | None = None,
) -> list[Path]:
    """Select local video clips matching mood/tags.

    Args:
        db: Active SQLAlchemy session.
        mood: Desired mood string (e.g. "eerie", "dreamy").
        tags: List of tag keywords to match against.
        count: How many clips to return (2–5, randomised if None).

    Returns:
        List of absolute Paths to downloaded video files.
    """
    settings = get_settings()
    wanted = count or random.randint(MIN_CLIPS, MAX_CLIPS)
    wanted = max(MIN_CLIPS, min(MAX_CLIPS, wanted))

    query = db.query(MediaAsset).filter(MediaAsset.downloaded.is_(True))

    # Build a pool of candidates using mood / tag scoring
    candidates = query.all()

    if not candidates:
        log.warning("No downloaded media assets in the database — falling back to filesystem scan")
        return _scan_media_library(wanted)

    scored: list[tuple[float, MediaAsset]] = []
    for asset in candidates:
        score = _relevance_score(asset, mood, tags)
        scored.append((score, asset))

    # Sort descending by score, then shuffle ties for variety
    scored.sort(key=lambda x: x[0], reverse=True)

    # Take top 3× wanted, then randomly pick from that pool
    pool_size = min(len(scored), wanted * 3)
    pool = scored[:pool_size]
    random.shuffle(pool)
    selected = pool[:wanted]

    paths: list[Path] = []
    for _, asset in selected:
        p = Path(asset.local_path) if asset.local_path else None
        if p and p.exists():
            paths.append(p)
        else:
            # Try conventional path
            lib = Path(settings.media_library_dir)
            guessed = lib / asset.source / f"{asset.source_id}.mp4"
            if guessed.exists():
                paths.append(guessed)
            else:
                log.warning("Asset %d (%s) — file not found on disk, skipping", asset.id, asset.title)

    if len(paths) < MIN_CLIPS:
        log.warning("Only %d clips from DB — supplementing with filesystem scan", len(paths))
        extras = _scan_media_library(MIN_CLIPS - len(paths), exclude=set(paths))
        paths.extend(extras)

    log.info("Selected %d video clips (mood=%s, tags=%s)", len(paths), mood, tags)
    return paths


def _relevance_score(
    asset: MediaAsset,
    mood: str | None,
    tags: list[str] | None,
) -> float:
    """Score an asset's relevance to the requested mood/tags (0.0–1.0)."""
    score = 0.0

    if mood and asset.mood:
        if mood.lower() in asset.mood.lower():
            score += 0.5
        # Partial match on words
        mood_words = set(mood.lower().split())
        asset_words = set(asset.mood.lower().split())
        if mood_words & asset_words:
            score += 0.2

    if tags and asset.tags:
        try:
            asset_tags = json.loads(asset.tags) if isinstance(asset.tags, str) else asset.tags
        except (json.JSONDecodeError, TypeError):
            asset_tags = []
        asset_tag_lower = {t.lower() for t in asset_tags}
        request_tag_lower = {t.lower() for t in tags}
        overlap = asset_tag_lower & request_tag_lower
        if overlap:
            score += 0.3 * (len(overlap) / len(request_tag_lower))

    # Small random jitter so identically-scored clips vary across runs
    score += random.uniform(0, 0.05)
    return min(score, 1.0)


def _scan_media_library(
    count: int,
    exclude: set[Path] | None = None,
) -> list[Path]:
    """Fallback: scan the media-library directory for any video files."""
    settings = get_settings()
    lib = Path(settings.media_library_dir)
    exclude = exclude or set()

    video_exts = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
    found: list[Path] = []

    if lib.exists():
        for f in lib.rglob("*"):
            if f.suffix.lower() in video_exts and f not in exclude:
                found.append(f)

    random.shuffle(found)
    result = found[:count]
    if result:
        log.info("Filesystem scan found %d video files", len(result))
    else:
        log.warning("No video files found in %s", lib)
    return result
