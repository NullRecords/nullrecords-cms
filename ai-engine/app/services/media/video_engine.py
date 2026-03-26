"""Video Engine — main orchestrator for the video generation pipeline.

Coordinates audio extraction, clip selection, effect application,
and rendering into a single generate_video() call.
"""

import logging
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.media.audio import extract_clip as extract_audio_clip
from app.services.media.clip_selector import select_clips
from app.services.media.renderer import render_video

log = logging.getLogger(__name__)


@dataclass
class VideoConfig:
    """Configuration for a single video generation run."""

    audio_path: str
    start_ms: int = 0
    duration_ms: int = 15000
    mood: str = ""
    tags: list[str] = field(default_factory=list)
    output_name: str = ""
    clip_count: int | None = None
    fps: int = 24
    use_glitch_transitions: bool = True
    aspect: str = "vertical"  # "vertical" (9:16) or "widescreen" (16:9)


class VideoEngine:
    """Local-first video generation engine.

    Usage::

        engine = VideoEngine()
        result = engine.generate_video(db, config)
        print(result)  # Path to exported video
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.exports_dir = Path(self.settings.exports_dir) / "videos"
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self._tmp_dir = Path(self.settings.exports_dir) / ".tmp"
        self._tmp_dir.mkdir(parents=True, exist_ok=True)

    def generate_video(self, db: Session, config: VideoConfig) -> Path:
        """Run the full video generation pipeline.

        Args:
            db: Active SQLAlchemy database session.
            config: Generation parameters.

        Returns:
            Path to the rendered video file.

        Raises:
            FileNotFoundError: If the audio file doesn't exist.
            RuntimeError: If no usable clips are found.
        """
        run_id = uuid.uuid4().hex[:8]
        log.info("═══ Video generation [%s] ═══", run_id)

        # ── 1. Validate audio ───────────────────────────────────────────
        audio_src = Path(config.audio_path)
        if not audio_src.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_src}")
        log.info("[%s] Audio source: %s", run_id, audio_src.name)

        # ── 2. Extract audio clip ───────────────────────────────────────
        audio_clip_path = self._tmp_dir / f"{run_id}_audio.wav"
        extract_audio_clip(
            audio_path=audio_src,
            start_ms=config.start_ms,
            duration_ms=config.duration_ms,
            output_path=audio_clip_path,
        )
        log.info("[%s] Audio clip extracted: %s", run_id, audio_clip_path.name)

        # ── 3. Select video clips ──────────────────────────────────────
        clip_paths = select_clips(
            db=db,
            mood=config.mood or None,
            tags=config.tags or None,
            count=config.clip_count,
        )
        if not clip_paths:
            raise RuntimeError(
                "No video clips available. Download media assets first via "
                "POST /media/search + POST /media/download/{id}"
            )
        log.info("[%s] Selected %d clips", run_id, len(clip_paths))

        # ── 4. Determine output path ───────────────────────────────────
        if config.output_name:
            out_name = config.output_name
            if not out_name.endswith(".mp4"):
                out_name += ".mp4"
        else:
            mood_slug = config.mood.replace(" ", "_")[:20] if config.mood else "mix"
            out_name = f"short_{mood_slug}_{run_id}.mp4"

        output_path = self.exports_dir / out_name

        # ── 5. Render ──────────────────────────────────────────────────
        result = render_video(
            clip_paths=clip_paths,
            audio_path=audio_clip_path,
            output_path=output_path,
            fps=config.fps,
            use_glitch_transitions=config.use_glitch_transitions,
            aspect=config.aspect,
        )

        # Clean up temp audio
        try:
            audio_clip_path.unlink(missing_ok=True)
        except OSError:
            pass

        log.info("═══ Video generation [%s] COMPLETE → %s ═══", run_id, result)
        return result

    def list_exports(self) -> list[dict]:
        """List all exported videos."""
        videos = []
        for f in sorted(self.exports_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True):
            stat = f.stat()
            videos.append({
                "filename": f.name,
                "path": str(f),
                "size_kb": round(stat.st_size / 1024, 1),
                "created": stat.st_mtime,
            })
        return videos
