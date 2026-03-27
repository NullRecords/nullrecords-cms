"""Video Engine — main orchestrator for the video generation pipeline.

Coordinates audio extraction, image sourcing, clip selection, text
overlay composition, effect application, and rendering into a single
generate_video() call.
"""

import logging
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.media.audio import extract_clip as extract_audio_clip
from app.services.media.clip_selector import select_clips
from app.services.media.image_source import fetch_images_for_video
from app.services.media.renderer import TextOverlay, render_video

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

    # Image sourcing
    image_query: str = ""            # Pexels search term (e.g. "cyberpunk city")
    image_urls: list[str] = field(default_factory=list)   # Direct image URLs
    image_paths: list[str] = field(default_factory=list)   # Local image file paths

    # Text overlays
    overlay_text: str = ""           # Main text (title / track name)
    overlay_subtitle: str = ""       # Subtitle (artist / link)
    overlay_position: str = "center" # center, top, bottom, lower-third

    # Effect configuration
    effect_opacity: float = 1.0
    glitch_opacity: float = 0.7
    color_shift_enabled: bool = False
    scanline_enabled: bool = False
    vhs_enabled: bool = False
    beat_flash_enabled: bool = False

    # Visualizer configuration
    visualizer_enabled: bool = False
    visualizer_type: str = "bars"     # bars, lines, waveform, circular
    visualizer_color: str = "#00ffff"
    visualizer_color2: str = "#ff5758"
    visualizer_opacity: float = 0.8
    visualizer_intensity: float = 1.0
    visualizer_position: str = "bottom"  # bottom, center, top, full
    visualizer_bar_count: int = 32
    visualizer_glow: bool = True
    show_song_info: bool = True

    # Font / style configuration
    font_family: str = ""
    title_color: str = ""
    subtitle_color: str = ""
    font_size_title: int = 0
    font_size_subtitle: int = 0
    text_spacing: int = 0


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
            RuntimeError: If no usable clips or images are found.
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

        # ── 3. Fetch images ────────────────────────────────────────────
        image_paths: list[Path] = []

        # Local image paths provided directly
        for p in config.image_paths:
            pp = Path(p)
            if pp.exists():
                image_paths.append(pp)
            else:
                log.warning("[%s] Image not found: %s", run_id, p)

        # Fetch from URLs or Pexels search
        if config.image_urls or config.image_query:
            fetched = fetch_images_for_video(
                query=config.image_query or None,
                image_urls=config.image_urls or None,
                count=config.clip_count or 3,
            )
            image_paths.extend(fetched)

        if image_paths:
            log.info("[%s] Using %d images", run_id, len(image_paths))

        # ── 4. Select video clips ──────────────────────────────────────
        clip_paths = select_clips(
            db=db,
            mood=config.mood or None,
            tags=config.tags or None,
            count=config.clip_count,
        )
        # If we have images, we can proceed even without video clips
        if not clip_paths and not image_paths:
            raise RuntimeError(
                "No video clips or images available. Download media assets first via "
                "POST /media/search + POST /media/download/{id}, or provide images."
            )
        log.info("[%s] Selected %d clips + %d images", run_id, len(clip_paths), len(image_paths))

        # ── 5. Analyze audio for beat-sync & visualizer ──────────────
        audio_data = None
        if config.beat_flash_enabled or config.visualizer_enabled:
            try:
                from app.services.media.audio_analyzer import analyze_audio
                audio_data = analyze_audio(str(audio_clip_path), fps=config.fps)
                log.info("[%s] Audio analyzed: %d beats, BPM=%.1f", run_id, len(audio_data["beats"]), audio_data["bpm"])
            except Exception as e:
                log.warning("[%s] Audio analysis failed, continuing without: %s", run_id, e)

        # ── 6. Build text overlays ─────────────────────────────────────
        text_overlays: list[TextOverlay] = []

        # AI mood-based color selection when not specified
        mood_colors = _mood_to_colors(config.mood)
        title_color = config.title_color or mood_colors["title"]
        subtitle_color = config.subtitle_color or mood_colors["subtitle"]
        title_size = config.font_size_title or 0  # 0 = auto in renderer
        subtitle_size = config.font_size_subtitle or 0

        if config.overlay_text:
            text_overlays.append(TextOverlay(
                text=config.overlay_text,
                position=config.overlay_position,
                color=title_color,
                shadow=True,
                font_size=title_size,
            ))
        if config.overlay_subtitle:
            text_overlays.append(TextOverlay(
                text=config.overlay_subtitle,
                position="lower-third" if config.overlay_position == "center" else "bottom",
                color=subtitle_color,
                shadow=True,
                font_size=subtitle_size,
            ))

        # ── 7. Build effect config ─────────────────────────────────────
        from app.services.media.effects import EffectConfig
        effect_config = EffectConfig(
            global_opacity=config.effect_opacity,
            glitch_opacity=config.glitch_opacity,
            color_shift_enabled=config.color_shift_enabled,
            color_shift_intensity=0.15,
            scanline_enabled=config.scanline_enabled,
            scanline_opacity=0.3,
            vhs_enabled=config.vhs_enabled,
            vhs_intensity=0.5,
            beat_flash_enabled=config.beat_flash_enabled,
            beat_flash_intensity=0.3,
        )

        # ── 8. Build visualizer config ─────────────────────────────────
        visualizer_config = None
        if config.visualizer_enabled and audio_data:
            visualizer_config = {
                "type": config.visualizer_type,
                "color": config.visualizer_color,
                "color2": config.visualizer_color2,
                "opacity": config.visualizer_opacity,
                "intensity": config.visualizer_intensity,
                "position": config.visualizer_position,
                "bar_count": config.visualizer_bar_count,
                "glow": config.visualizer_glow,
                "show_song_info": config.show_song_info,
                "song_title": config.overlay_text,
                "artist": config.overlay_subtitle,
                "spectrum": audio_data["spectrum"],
                "levels": audio_data["levels"],
                "beats": audio_data["beats"],
                "fps": audio_data["fps"],
                "n_frames": audio_data["n_frames"],
            }

        # ── 9. Determine output path ───────────────────────────────────
        if config.output_name:
            out_name = config.output_name
            if not out_name.endswith(".mp4"):
                out_name += ".mp4"
        else:
            mood_slug = config.mood.replace(" ", "_")[:20] if config.mood else "mix"
            out_name = f"short_{mood_slug}_{run_id}.mp4"

        output_path = self.exports_dir / out_name

        # ── 10. Render ─────────────────────────────────────────────────
        result = render_video(
            clip_paths=clip_paths,
            audio_path=audio_clip_path,
            output_path=output_path,
            fps=config.fps,
            use_glitch_transitions=config.use_glitch_transitions,
            aspect=config.aspect,
            image_paths=image_paths,
            text_overlays=text_overlays,
            effect_config=effect_config,
            visualizer_config=visualizer_config,
            audio_data=audio_data,
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


def _mood_to_colors(mood: str) -> dict:
    """AI-selected color palette based on mood keywords."""
    m = mood.lower().strip() if mood else ""
    if any(w in m for w in ("dark", "ambient", "chill", "lofi")):
        return {"title": "#ffffff", "subtitle": "#00ffff"}
    if any(w in m for w in ("energetic", "hype", "edm", "punk")):
        return {"title": "#ff5758", "subtitle": "#ffeb3b"}
    if any(w in m for w in ("dreamy", "space", "ethereal", "cosmic")):
        return {"title": "#e0b0ff", "subtitle": "#00ffff"}
    if any(w in m for w in ("aggressive", "metal", "industrial")):
        return {"title": "#ff5758", "subtitle": "#ffffff"}
    if any(w in m for w in ("retro", "synthwave", "80s", "vaporwave")):
        return {"title": "#ff00ff", "subtitle": "#00ffff"}
    if any(w in m for w in ("happy", "upbeat", "pop")):
        return {"title": "#ffffff", "subtitle": "#ED7512"}
    # Default — NullRecords brand colors
    return {"title": "#ffffff", "subtitle": "#00ffff"}
