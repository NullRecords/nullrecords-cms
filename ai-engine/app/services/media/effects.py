"""Cinematic visual effects — composable transforms for video clips.

All effects accept a MoviePy VideoClip and return a new clip.
Effects are designed to be chained: grain_overlay(zoom_effect(clip)).
"""

import logging
import random

import numpy as np
from moviepy import (
    VideoClip,
    concatenate_videoclips,
)

log = logging.getLogger(__name__)


# ── Ken Burns zoom ──────────────────────────────────────────────────────────

def zoom_effect(clip: VideoClip, zoom_ratio: float = 0.04) -> VideoClip:
    """Apply a slow zoom-in (Ken Burns) effect.

    Args:
        clip: Source video clip.
        zoom_ratio: Total zoom increase over the clip duration (0.04 = 4%).

    Returns:
        New clip with the zoom applied.
    """
    duration = clip.duration
    w, h = clip.size

    def _zoom_frame(get_frame, t):
        progress = t / duration if duration > 0 else 0
        scale = 1 + zoom_ratio * progress
        frame = get_frame(t)

        # Crop to simulate zoom
        new_w = int(w / scale)
        new_h = int(h / scale)
        x1 = (w - new_w) // 2
        y1 = (h - new_h) // 2
        cropped = frame[y1 : y1 + new_h, x1 : x1 + new_w]

        # Resize back to original dimensions
        from PIL import Image

        img = Image.fromarray(cropped)
        img = img.resize((w, h), Image.LANCZOS)
        return np.array(img)

    zoomed = clip.transform(_zoom_frame)
    log.info("Applied zoom effect (ratio=%.2f)", zoom_ratio)
    return zoomed


# ── Flicker effect ──────────────────────────────────────────────────────────

def flicker_effect(clip: VideoClip, intensity: float = 0.06) -> VideoClip:
    """Apply a subtle brightness flicker over time.

    Simulates a film projector flicker by randomly varying brightness
    per-frame within a narrow band.

    Args:
        clip: Source video clip.
        intensity: Maximum brightness shift (0.06 = ±6%).

    Returns:
        New clip with flicker applied.
    """
    # Pre-generate per-frame flicker values for consistency across seeks
    fps = clip.fps or 24
    n_frames = int((clip.duration or 1) * fps) + 1
    rng = np.random.default_rng(seed=42)
    flicker_vals = 1.0 + rng.uniform(-intensity, intensity, size=n_frames)

    def _flicker_frame(get_frame, t):
        frame = get_frame(t).astype(np.float32)
        idx = min(int(t * fps), n_frames - 1)
        frame = frame * flicker_vals[idx]
        return np.clip(frame, 0, 255).astype(np.uint8)

    flickered = clip.transform(_flicker_frame)
    log.info("Applied flicker effect (intensity=%.2f)", intensity)
    return flickered


# ── Film grain overlay ──────────────────────────────────────────────────────

def grain_overlay(clip: VideoClip, strength: float = 12.0) -> VideoClip:
    """Add simulated film grain noise to the clip.

    Args:
        clip: Source video clip.
        strength: Standard deviation of the grain noise (12.0 = subtle).

    Returns:
        New clip with grain applied.
    """
    w, h = clip.size
    rng = np.random.default_rng()

    def _grain_frame(get_frame, t):
        frame = get_frame(t).astype(np.float32)
        noise = rng.normal(0, strength, frame.shape).astype(np.float32)
        frame = frame + noise
        return np.clip(frame, 0, 255).astype(np.uint8)

    grained = clip.transform(_grain_frame)
    log.info("Applied grain overlay (strength=%.1f)", strength)
    return grained


# ── Glitch transition ──────────────────────────────────────────────────────

def glitch_transition(
    clip1: VideoClip,
    clip2: VideoClip,
    glitch_duration: float = 0.3,
) -> VideoClip:
    """Create a quick glitch-style transition between two clips.

    Produces a short segment of distorted frames spliced between the clips.

    Args:
        clip1: Outgoing clip.
        clip2: Incoming clip.
        glitch_duration: Duration of the glitch burst in seconds.

    Returns:
        Concatenated clip: clip1 → glitch → clip2.
    """
    w, h = clip1.size
    fps = clip1.fps or 24
    n_frames = max(int(glitch_duration * fps), 2)
    rng = np.random.default_rng()

    # Build glitch frames from the tail of clip1 and head of clip2
    frames = []
    for i in range(n_frames):
        mix = i / n_frames
        t1 = max(0, clip1.duration - 0.1)
        t2 = min(0.1, clip2.duration)

        # Alternate between distorted frames from each clip
        if rng.random() > mix:
            base = clip1.get_frame(t1)
        else:
            base = clip2.get_frame(t2)

        # Horizontal shift glitch
        shift = rng.integers(-30, 30)
        glitched = np.roll(base, shift, axis=1)

        # Random color channel offset
        ch = rng.integers(0, 3)
        ch_shift = rng.integers(-10, 10)
        glitched[:, :, ch] = np.roll(glitched[:, :, ch], ch_shift, axis=1)

        # Occasional scanline corruption
        if rng.random() > 0.5:
            row = rng.integers(0, h)
            thickness = rng.integers(1, 6)
            glitched[row : row + thickness, :] = rng.integers(0, 255, size=(min(thickness, h - row), w, 3))

        frames.append(glitched)

    from moviepy import ImageSequenceClip

    glitch_clip = ImageSequenceClip(frames, fps=fps)
    result = concatenate_videoclips([clip1, glitch_clip, clip2], method="compose")
    log.info("Applied glitch transition (%.1fs)", glitch_duration)
    return result


# ── Composable effect pipeline ──────────────────────────────────────────────

DEFAULT_EFFECTS = [zoom_effect, flicker_effect, grain_overlay]


def apply_effects(
    clip: VideoClip,
    effects: list | None = None,
) -> VideoClip:
    """Apply a chain of effects to a clip.

    Args:
        clip: Source video clip.
        effects: List of effect functions to apply in order.
                 Defaults to [zoom, flicker, grain].

    Returns:
        Clip with all effects applied.
    """
    effects = effects if effects is not None else DEFAULT_EFFECTS
    for fx in effects:
        clip = fx(clip)
    return clip
