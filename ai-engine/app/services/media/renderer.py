"""Video renderer — composes clips into a final vertical short-form video.

Handles clip loading, trimming, resizing to 9:16, effect application,
concatenation, audio attachment, and H.264/AAC export.
"""

import logging
import random
from pathlib import Path

import numpy as np
from moviepy import (
    AudioFileClip,
    VideoFileClip,
    concatenate_videoclips,
)
from PIL import Image

from app.services.media.effects import apply_effects, glitch_transition

log = logging.getLogger(__name__)

# ── Constants ───────────────────────────────────────────────────────────────
TARGET_FPS = 24
MIN_CLIP_DURATION = 3.0   # seconds
MAX_CLIP_DURATION = 8.0

PRESETS = {
    "vertical": (1080, 1920),   # 9:16 — TikTok/Reels/Shorts
    "widescreen": (1920, 1080), # 16:9 — YouTube landscape
}


def render_video(
    clip_paths: list[Path],
    audio_path: Path | None,
    output_path: Path,
    fps: int = TARGET_FPS,
    use_glitch_transitions: bool = True,
    aspect: str = "vertical",
) -> Path:
    """Render a vertical short-form video from clips + audio.

    Steps:
        1. Load each video clip.
        2. Trim to 3–8 seconds.
        3. Resize / letterbox to 1080×1920.
        4. Apply cinematic effects.
        5. Concatenate (with optional glitch transitions).
        6. Attach audio track.
        7. Export H.264 / AAC.

    Args:
        clip_paths: Paths to source video files (2–5).
        audio_path: Path to audio clip (WAV/MP3). None for silent video.
        output_path: Where to write the final .mp4.
        fps: Output frame rate.
        use_glitch_transitions: Insert glitch transitions between clips.

    Returns:
        Path to the exported video file.
    """
    if not clip_paths:
        raise ValueError("No clip paths provided")

    target_w, target_h = PRESETS.get(aspect, PRESETS["vertical"])
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    log.info("Rendering video from %d clips → %s (%s %dx%d)", len(clip_paths), output_path.name, aspect, target_w, target_h)

    # ── 1. Load & prepare clips ─────────────────────────────────────────
    prepared: list = []
    for i, cp in enumerate(clip_paths):
        log.info("  [%d/%d] Loading %s", i + 1, len(clip_paths), cp.name)
        try:
            raw = VideoFileClip(str(cp))
        except Exception as exc:
            log.warning("  Skipping %s — failed to load: %s", cp.name, exc)
            continue

        # Trim
        trimmed = _trim_clip(raw)
        # Resize to target aspect
        resized = _resize_clip(trimmed, target_w, target_h)
        # Apply effects
        with_fx = apply_effects(resized)

        prepared.append(with_fx)

    if not prepared:
        raise RuntimeError("No clips could be loaded — cannot render video")

    # ── 2. Concatenate ──────────────────────────────────────────────────
    if use_glitch_transitions and len(prepared) > 1:
        final_video = _concat_with_glitch(prepared)
    else:
        final_video = concatenate_videoclips(prepared, method="compose")

    # ── 3. Attach audio ─────────────────────────────────────────────────
    if audio_path and audio_path.exists():
        log.info("Attaching audio: %s", audio_path.name)
        audio_clip = AudioFileClip(str(audio_path))
        # Trim audio to video length
        if audio_clip.duration > final_video.duration:
            audio_clip = audio_clip.subclipped(0, final_video.duration)
        final_video = final_video.with_audio(audio_clip)
    else:
        log.info("No audio — rendering silent video")

    # ── 4. Export ────────────────────────────────────────────────────────
    log.info("Exporting video: %s (%.1fs, %dx%d @ %dfps)",
             output_path.name, final_video.duration,
             final_video.w, final_video.h, fps)

    final_video.write_videofile(
        str(output_path),
        fps=fps,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        threads=4,
        logger=None,  # suppress moviepy's noisy output
    )

    # Cleanup
    final_video.close()
    for c in prepared:
        c.close()

    log.info("✓ Video rendered: %s (%.1f KB)", output_path.name, output_path.stat().st_size / 1024)
    return output_path


# ── Internal helpers ────────────────────────────────────────────────────────

def _trim_clip(clip: VideoFileClip) -> VideoFileClip:
    """Trim clip to 3–8 seconds, picking a random window if longer."""
    duration = clip.duration or 0
    if duration <= 0:
        return clip

    target = random.uniform(MIN_CLIP_DURATION, MAX_CLIP_DURATION)
    if duration <= target:
        return clip

    # Random start point
    max_start = duration - target
    start = random.uniform(0, max_start)
    trimmed = clip.subclipped(start, start + target)
    log.info("    Trimmed %.1fs → %.1fs (start=%.1fs)", duration, target, start)
    return trimmed


def _resize_clip(clip: VideoFileClip, target_w: int, target_h: int) -> VideoFileClip:
    """Resize clip to target dimensions. Crops to fill, no letterboxing."""
    w, h = clip.size
    target_ratio = target_w / target_h

    src_ratio = w / h

    if abs(src_ratio - target_ratio) < 0.01:
        # Already correct ratio — just resize
        return clip.resized((target_w, target_h))

    if src_ratio > target_ratio:
        # Source is wider — crop sides
        new_w = int(h * target_ratio)
        x_offset = (w - new_w) // 2
        cropped = clip.cropped(x1=x_offset, x2=x_offset + new_w)
    else:
        # Source is taller — crop top/bottom
        new_h = int(w / target_ratio)
        y_offset = (h - new_h) // 2
        cropped = clip.cropped(y1=y_offset, y2=y_offset + new_h)

    return cropped.resized((target_w, target_h))


def _concat_with_glitch(clips: list) -> VideoFileClip:
    """Concatenate clips with glitch transitions between each pair."""
    if len(clips) == 1:
        return clips[0]

    result = clips[0]
    for i in range(1, len(clips)):
        result = glitch_transition(result, clips[i], glitch_duration=0.25)

    return result
