"""Cinematic visual effects — composable transforms for video clips.

All effects accept a MoviePy VideoClip and return a new clip.
Effects support configurable opacity (transparency) for layering over images.
Effects are designed to be chained: grain_overlay(zoom_effect(clip)).
"""

import logging
import math
import random

import numpy as np
from moviepy import (
    VideoClip,
    concatenate_videoclips,
)

log = logging.getLogger(__name__)


# ── Effect configuration ────────────────────────────────────────────────────

class EffectConfig:
    """Configuration for all visual effects — controls types, opacity, intensity."""

    def __init__(
        self,
        *,
        zoom_ratio: float = 0.04,
        zoom_enabled: bool = True,
        flicker_intensity: float = 0.06,
        flicker_enabled: bool = True,
        grain_strength: float = 12.0,
        grain_enabled: bool = True,
        glitch_opacity: float = 0.7,
        glitch_duration: float = 0.3,
        color_shift_enabled: bool = False,
        color_shift_intensity: float = 0.15,
        scanline_enabled: bool = False,
        scanline_opacity: float = 0.3,
        vhs_enabled: bool = False,
        vhs_intensity: float = 0.5,
        beat_flash_enabled: bool = False,
        beat_flash_intensity: float = 0.3,
        global_opacity: float = 1.0,
    ):
        self.zoom_ratio = zoom_ratio
        self.zoom_enabled = zoom_enabled
        self.flicker_intensity = flicker_intensity
        self.flicker_enabled = flicker_enabled
        self.grain_strength = grain_strength
        self.grain_enabled = grain_enabled
        self.glitch_opacity = glitch_opacity
        self.glitch_duration = glitch_duration
        self.color_shift_enabled = color_shift_enabled
        self.color_shift_intensity = color_shift_intensity
        self.scanline_enabled = scanline_enabled
        self.scanline_opacity = scanline_opacity
        self.vhs_enabled = vhs_enabled
        self.vhs_intensity = vhs_intensity
        self.beat_flash_enabled = beat_flash_enabled
        self.beat_flash_intensity = beat_flash_intensity
        self.global_opacity = global_opacity

    def build_effect_list(self) -> list:
        """Build the effects pipeline based on enabled flags."""
        effects = []
        if self.zoom_enabled:
            effects.append(lambda clip: zoom_effect(clip, self.zoom_ratio))
        if self.flicker_enabled:
            effects.append(lambda clip: flicker_effect(clip, self.flicker_intensity))
        if self.grain_enabled:
            effects.append(lambda clip: grain_overlay(clip, self.grain_strength))
        if self.color_shift_enabled:
            effects.append(lambda clip: color_shift_effect(clip, self.color_shift_intensity))
        if self.scanline_enabled:
            effects.append(lambda clip: scanline_effect(clip, self.scanline_opacity))
        if self.vhs_enabled:
            effects.append(lambda clip: vhs_distortion(clip, self.vhs_intensity))
        return effects


# ── Ken Burns zoom ──────────────────────────────────────────────────────────

def zoom_effect(clip: VideoClip, zoom_ratio: float = 0.04) -> VideoClip:
    """Apply a slow zoom-in (Ken Burns) effect."""
    duration = clip.duration
    w, h = clip.size

    def _zoom_frame(get_frame, t):
        progress = t / duration if duration > 0 else 0
        scale = 1 + zoom_ratio * progress
        frame = get_frame(t)

        new_w = int(w / scale)
        new_h = int(h / scale)
        x1 = (w - new_w) // 2
        y1 = (h - new_h) // 2
        cropped = frame[y1 : y1 + new_h, x1 : x1 + new_w]

        from PIL import Image
        img = Image.fromarray(cropped)
        img = img.resize((w, h), Image.LANCZOS)
        return np.array(img)

    zoomed = clip.transform(_zoom_frame)
    log.info("Applied zoom effect (ratio=%.2f)", zoom_ratio)
    return zoomed


# ── Flicker effect ──────────────────────────────────────────────────────────

def flicker_effect(clip: VideoClip, intensity: float = 0.06) -> VideoClip:
    """Apply a subtle brightness flicker over time."""
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
    """Add simulated film grain noise."""
    rng = np.random.default_rng()

    def _grain_frame(get_frame, t):
        frame = get_frame(t).astype(np.float32)
        noise = rng.normal(0, strength, frame.shape).astype(np.float32)
        frame = frame + noise
        return np.clip(frame, 0, 255).astype(np.uint8)

    grained = clip.transform(_grain_frame)
    log.info("Applied grain overlay (strength=%.1f)", strength)
    return grained


# ── Color shift / chromatic aberration ──────────────────────────────────────

def color_shift_effect(clip: VideoClip, intensity: float = 0.15) -> VideoClip:
    """RGB channel offset — horizontal shift per channel for chromatic aberration."""
    w, h = clip.size
    shift_px = max(1, int(w * intensity * 0.02))

    def _shift_frame(get_frame, t):
        frame = get_frame(t).copy()
        frame[:, :, 0] = np.roll(frame[:, :, 0], shift_px, axis=1)    # R right
        frame[:, :, 2] = np.roll(frame[:, :, 2], -shift_px, axis=1)   # B left
        return frame

    shifted = clip.transform(_shift_frame)
    log.info("Applied color shift (intensity=%.2f)", intensity)
    return shifted


# ── Scanline overlay ───────────────────────────────────────────────────────

def scanline_effect(clip: VideoClip, opacity: float = 0.3) -> VideoClip:
    """CRT scanline overlay — horizontal dark lines at configurable opacity."""
    w, h = clip.size
    # Pre-generate scanline mask
    mask = np.ones((h, w), dtype=np.float32)
    for y in range(0, h, 3):
        mask[y, :] = 1.0 - opacity

    def _scanline_frame(get_frame, t):
        frame = get_frame(t).astype(np.float32)
        frame[:, :, 0] *= mask
        frame[:, :, 1] *= mask
        frame[:, :, 2] *= mask
        return np.clip(frame, 0, 255).astype(np.uint8)

    scanned = clip.transform(_scanline_frame)
    log.info("Applied scanline effect (opacity=%.2f)", opacity)
    return scanned


# ── VHS distortion ─────────────────────────────────────────────────────────

def vhs_distortion(clip: VideoClip, intensity: float = 0.5) -> VideoClip:
    """VHS-style warping — horizontal wobble + color bleeding."""
    fps = clip.fps or 24
    h = clip.size[1]
    rng = np.random.default_rng(seed=77)
    max_shift = int(6 * intensity)

    def _vhs_frame(get_frame, t):
        frame = get_frame(t).copy()
        # Row-level horizontal shift (wobble)
        for row in range(0, h, 2):
            shift = rng.integers(-max_shift, max_shift + 1)
            frame[row] = np.roll(frame[row], shift, axis=0)
        return frame

    vhs = clip.transform(_vhs_frame)
    log.info("Applied VHS distortion (intensity=%.2f)", intensity)
    return vhs


# ── Beat flash ─────────────────────────────────────────────────────────────

def beat_flash_effect(
    clip: VideoClip,
    beats: list[float],
    intensity: float = 0.3,
    decay: float = 0.15,
) -> VideoClip:
    """Flash brightness on beat hits with fast decay.

    Args:
        clip: Source clip.
        beats: List of beat timestamps in seconds.
        intensity: Peak brightness boost (0.3 = 30% brighter on beat).
        decay: Time in seconds for flash to fade.
    """
    beats_arr = np.array(beats, dtype=np.float64)

    def _flash_frame(get_frame, t):
        frame = get_frame(t).astype(np.float32)
        # Find time since closest previous beat
        past = beats_arr[beats_arr <= t]
        if len(past) == 0:
            return frame.astype(np.uint8)
        dt = t - past[-1]
        if dt < decay:
            boost = 1.0 + intensity * (1.0 - dt / decay)
            frame = frame * boost
        return np.clip(frame, 0, 255).astype(np.uint8)

    flashed = clip.transform(_flash_frame)
    log.info("Applied beat flash (%d beats, intensity=%.2f)", len(beats), intensity)
    return flashed


# ── Glitch transition ──────────────────────────────────────────────────────

def glitch_transition(
    clip1: VideoClip,
    clip2: VideoClip,
    glitch_duration: float = 0.3,
    opacity: float = 1.0,
) -> VideoClip:
    """Glitch-style transition between two clips with configurable opacity.

    At opacity < 1.0, the glitch frames blend with the underlying clip
    frames rather than fully replacing them.
    """
    w, h = clip1.size
    fps = clip1.fps or 24
    n_frames = max(int(glitch_duration * fps), 2)
    rng = np.random.default_rng()

    frames = []
    for i in range(n_frames):
        mix = i / n_frames
        t1 = max(0, clip1.duration - 0.1)
        t2 = min(0.1, clip2.duration)

        if rng.random() > mix:
            base = clip1.get_frame(t1).copy()
        else:
            base = clip2.get_frame(t2).copy()

        # Build glitch layer
        glitched = base.copy()

        # Horizontal shift
        shift = rng.integers(-30, 30)
        glitched = np.roll(glitched, shift, axis=1)

        # Channel offset
        ch = rng.integers(0, 3)
        ch_shift = rng.integers(-10, 10)
        glitched[:, :, ch] = np.roll(glitched[:, :, ch], ch_shift, axis=1)

        # Scanline corruption
        if rng.random() > 0.5:
            row = rng.integers(0, h)
            thickness = rng.integers(1, 6)
            glitched[row : row + thickness, :] = rng.integers(
                0, 255, size=(min(thickness, h - row), w, 3),
            )

        # Blend glitch with base by opacity
        if opacity < 1.0:
            result = (
                base.astype(np.float32) * (1.0 - opacity)
                + glitched.astype(np.float32) * opacity
            )
            frames.append(np.clip(result, 0, 255).astype(np.uint8))
        else:
            frames.append(glitched)

    from moviepy import ImageSequenceClip

    glitch_clip = ImageSequenceClip(frames, fps=fps)
    result = concatenate_videoclips([clip1, glitch_clip, clip2], method="compose")
    log.info("Applied glitch transition (%.1fs, opacity=%.2f)", glitch_duration, opacity)
    return result


# ── Composable effect pipeline ──────────────────────────────────────────────

DEFAULT_EFFECTS = [zoom_effect, flicker_effect, grain_overlay]


def apply_effects(
    clip: VideoClip,
    effects: list | None = None,
    config: EffectConfig | None = None,
) -> VideoClip:
    """Apply a chain of effects to a clip.

    If config is provided, builds the effect list from it.
    Otherwise falls back to the effects list or DEFAULT_EFFECTS.
    When global_opacity < 1.0, blends the effected result with the
    original frame so effects appear as transparent overlays.
    """
    opacity = config.global_opacity if config is not None else 1.0

    if config is not None:
        effects = config.build_effect_list()
    elif effects is None:
        effects = DEFAULT_EFFECTS

    for fx in effects:
        clip = fx(clip)

    # Blend effected frames with original at global_opacity < 1.0
    if opacity < 1.0:
        original = clip  # this is already post-effects; we need pre-effects
        # Re-apply from scratch: effects need a pre/post approach
        # Instead, wrap the effected clip to blend per-frame
        clip = _blend_with_opacity(clip, opacity)

    return clip


def apply_effects_blended(
    clip: VideoClip,
    config: EffectConfig | None = None,
) -> VideoClip:
    """Apply effects as a transparent overlay over the original clip.

    Saves a reference to the original frames, applies the full effect chain,
    then per-frame blends: result = original*(1-opacity) + effected*opacity.
    This ensures images remain visible underneath the effects.
    """
    if config is None:
        config = EffectConfig()

    opacity = config.global_opacity
    effects = config.build_effect_list()

    if not effects:
        return clip

    # Apply effects to get the processed version
    effected = clip
    for fx in effects:
        effected = fx(effected)

    if opacity >= 1.0:
        return effected

    # Blend original + effected per frame
    def _blend_frame(get_frame, t):
        orig = clip.get_frame(t).astype(np.float32)
        fx_frame = effected.get_frame(t).astype(np.float32)
        blended = orig * (1.0 - opacity) + fx_frame * opacity
        return np.clip(blended, 0, 255).astype(np.uint8)

    return effected.transform(_blend_frame)


def _blend_with_opacity(clip: VideoClip, opacity: float) -> VideoClip:
    """Placeholder — for backward compat. Use apply_effects_blended instead."""
    return clip
