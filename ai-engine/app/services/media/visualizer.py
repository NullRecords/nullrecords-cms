"""EQ Visualizer — renders audio spectrum data as visual overlays on video frames.

Supports multiple visualizer types:
- bars: Classic EQ bars rising from bottom
- lines: Connected line waveform
- waveform: Mirrored waveform (top and bottom reflection)
- circular: Radial spectrum around a center point

Each renders per-frame using spectrum data from audio_analyzer.
"""

import logging
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

log = logging.getLogger(__name__)


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert '#rrggbb' to (r, g, b) tuple."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return (0, 255, 255)  # fallback cyan
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def lerp_color(
    c1: tuple[int, int, int],
    c2: tuple[int, int, int],
    t: float,
) -> tuple[int, int, int]:
    """Linear interpolation between two RGB colors."""
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


def render_visualizer_frame(
    frame: np.ndarray,
    frame_idx: int,
    config: dict,
) -> np.ndarray:
    """Render the visualizer overlay onto a single video frame.

    Args:
        frame: RGB numpy array (H, W, 3) uint8.
        frame_idx: Current frame index (0-based).
        config: Visualizer config dict with spectrum, levels, etc.

    Returns:
        Frame with visualizer composited at the configured opacity.
    """
    h, w = frame.shape[:2]
    spectrum = config["spectrum"]
    n_frames = config["n_frames"]

    # Clamp frame index
    idx = min(frame_idx, n_frames - 1, len(spectrum) - 1)
    bands = spectrum[idx] if idx < len(spectrum) else [0.0] * 8

    level = config["levels"][idx] if idx < len(config["levels"]) else 0.0
    intensity = config.get("intensity", 1.0)
    opacity = config.get("opacity", 0.8)
    viz_type = config.get("type", "bars")

    # Check if this is a beat frame
    beats = config.get("beats", [])
    fps = config.get("fps", 24)
    is_beat = any(abs(frame_idx / fps - b) < 0.5 / fps for b in beats)

    # Create RGBA overlay
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    color1 = hex_to_rgb(config.get("color", "#00ffff"))
    color2 = hex_to_rgb(config.get("color2", "#ff5758"))
    bar_count = config.get("bar_count", 32)
    position = config.get("position", "bottom")
    glow = config.get("glow", True)

    # Interpolate bands to match bar_count
    if len(bands) < bar_count:
        interp_bands = np.interp(
            np.linspace(0, len(bands) - 1, bar_count),
            np.arange(len(bands)),
            bands,
        )
    else:
        interp_bands = np.array(bands[:bar_count])

    # Apply intensity and beat boost
    interp_bands = interp_bands * intensity
    if is_beat:
        interp_bands = interp_bands * 1.4

    if viz_type == "bars":
        _draw_bars(draw, w, h, interp_bands, color1, color2, position, glow, level)
    elif viz_type == "lines":
        _draw_lines(draw, w, h, interp_bands, color1, color2, position, level)
    elif viz_type == "waveform":
        _draw_waveform(draw, w, h, interp_bands, color1, color2, position, level)
    elif viz_type == "circular":
        _draw_circular(draw, w, h, interp_bands, color1, color2, level)

    # Render song info ONLY if no separate text overlays are applied
    # (text overlays are handled by the renderer's _apply_text_overlays)
    if config.get("show_song_info") and not config.get("skip_song_info") and (config.get("song_title") or config.get("artist")):
        _draw_song_info(draw, w, h, config.get("song_title", ""), config.get("artist", ""), color1)

    # Apply glow by blurring + adding
    if glow:
        glow_layer = overlay.filter(ImageFilter.GaussianBlur(radius=4))
        overlay = Image.alpha_composite(glow_layer, overlay)

    # Composite onto frame with opacity
    base = Image.fromarray(frame).convert("RGBA")
    # Adjust overlay alpha by global opacity
    r, g, b, a = overlay.split()
    a = a.point(lambda x: int(x * opacity))
    overlay = Image.merge("RGBA", (r, g, b, a))

    result = Image.alpha_composite(base, overlay)
    return np.array(result.convert("RGB"))


# ── Visualizer types ────────────────────────────────────────────────────────

def _draw_bars(
    draw: ImageDraw.ImageDraw,
    w: int,
    h: int,
    bands: np.ndarray,
    color1: tuple,
    color2: tuple,
    position: str,
    glow: bool,
    level: float,
):
    """Classic EQ bars visualization."""
    n = len(bands)
    gap = max(2, w // (n * 6))
    bar_w = max(3, (w - gap * (n + 1)) // n)
    max_bar_h = int(h * 0.35)

    # Position offset
    if position == "top":
        base_y = int(h * 0.05)
        direction = 1  # bars go down
    elif position == "center":
        base_y = h // 2
        direction = 0  # bars go both ways
    else:  # bottom (default)
        base_y = int(h * 0.95)
        direction = -1  # bars go up

    for i, val in enumerate(bands):
        x = gap + i * (bar_w + gap)
        bar_h = int(min(val, 1.0) * max_bar_h)
        if bar_h < 2:
            bar_h = 2

        # Gradient color per bar
        t = i / max(n - 1, 1)
        color = lerp_color(color1, color2, t)

        if direction == -1:  # bottom
            draw.rectangle([x, base_y - bar_h, x + bar_w, base_y], fill=(*color, 220))
            # Cap highlight
            draw.rectangle([x, base_y - bar_h, x + bar_w, base_y - bar_h + 3], fill=(255, 255, 255, 180))
        elif direction == 1:  # top
            draw.rectangle([x, base_y, x + bar_w, base_y + bar_h], fill=(*color, 220))
            draw.rectangle([x, base_y + bar_h - 3, x + bar_w, base_y + bar_h], fill=(255, 255, 255, 180))
        else:  # center
            half = bar_h // 2
            draw.rectangle([x, base_y - half, x + bar_w, base_y + half], fill=(*color, 200))


def _draw_lines(
    draw: ImageDraw.ImageDraw,
    w: int,
    h: int,
    bands: np.ndarray,
    color1: tuple,
    color2: tuple,
    position: str,
    level: float,
):
    """Connected line waveform visualization."""
    n = len(bands)
    max_amp = int(h * 0.3)

    if position == "top":
        center_y = int(h * 0.15)
    elif position == "center":
        center_y = h // 2
    else:
        center_y = int(h * 0.85)

    points = []
    for i, val in enumerate(bands):
        x = int(i / (n - 1) * (w - 1)) if n > 1 else w // 2
        y = center_y - int(min(val, 1.0) * max_amp)
        points.append((x, y))

    # Draw thick line
    if len(points) >= 2:
        for width, alpha in [(6, 80), (3, 180), (1, 255)]:
            draw.line(points, fill=(*color1, alpha), width=width)

    # Draw dots at peaks
    for x, y in points:
        draw.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(*color2, 200))


def _draw_waveform(
    draw: ImageDraw.ImageDraw,
    w: int,
    h: int,
    bands: np.ndarray,
    color1: tuple,
    color2: tuple,
    position: str,
    level: float,
):
    """Mirrored waveform — reflection above and below center line."""
    n = len(bands)
    max_amp = int(h * 0.2)

    if position == "top":
        center_y = int(h * 0.2)
    elif position == "center":
        center_y = h // 2
    else:
        center_y = int(h * 0.8)

    # Top half
    top_points = [(0, center_y)]
    for i, val in enumerate(bands):
        x = int(i / (n - 1) * (w - 1)) if n > 1 else w // 2
        y = center_y - int(min(val, 1.0) * max_amp)
        top_points.append((x, y))
    top_points.append((w - 1, center_y))

    # Bottom half (mirror)
    bot_points = [(0, center_y)]
    for i, val in enumerate(bands):
        x = int(i / (n - 1) * (w - 1)) if n > 1 else w // 2
        y = center_y + int(min(val, 1.0) * max_amp)
        bot_points.append((x, y))
    bot_points.append((w - 1, center_y))

    draw.polygon(top_points, fill=(*color1, 120))
    draw.polygon(bot_points, fill=(*color2, 100))

    # Outline
    if len(top_points) >= 2:
        draw.line(top_points, fill=(*color1, 200), width=2)
        draw.line(bot_points, fill=(*color2, 180), width=2)


def _draw_circular(
    draw: ImageDraw.ImageDraw,
    w: int,
    h: int,
    bands: np.ndarray,
    color1: tuple,
    color2: tuple,
    level: float,
):
    """Radial/circular spectrum visualization."""
    cx, cy = w // 2, h // 2
    base_r = min(w, h) * 0.12
    max_ext = min(w, h) * 0.25
    n = len(bands)

    # Inner circle
    r0 = int(base_r)
    draw.ellipse([cx - r0, cy - r0, cx + r0, cy + r0], outline=(*color1, 100), width=2)

    # Radial bars
    for i, val in enumerate(bands):
        angle = (2.0 * math.pi * i / n) - math.pi / 2
        ext = min(val, 1.0) * max_ext
        x1 = cx + math.cos(angle) * base_r
        y1 = cy + math.sin(angle) * base_r
        x2 = cx + math.cos(angle) * (base_r + ext)
        y2 = cy + math.sin(angle) * (base_r + ext)

        t = i / max(n - 1, 1)
        color = lerp_color(color1, color2, t)
        draw.line([(x1, y1), (x2, y2)], fill=(*color, 220), width=3)

    # Level glow ring
    glow_r = int(base_r + level * max_ext * 0.5)
    draw.ellipse(
        [cx - glow_r, cy - glow_r, cx + glow_r, cy + glow_r],
        outline=(*color2, int(100 * level)),
        width=2,
    )


# ── Song info overlay ──────────────────────────────────────────────────────

def _draw_song_info(
    draw: ImageDraw.ImageDraw,
    w: int,
    h: int,
    title: str,
    artist: str,
    color: tuple,
):
    """Draw song title and artist name on the visualizer."""
    # Try to load a nice font, fall back to default
    font_title = None
    font_artist = None
    try:
        font_title = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
        font_artist = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
    except (OSError, IOError):
        pass

    y_pos = int(h * 0.06)

    if title:
        bbox = draw.textbbox((0, 0), title, font=font_title)
        tw = bbox[2] - bbox[0]
        draw.text(
            ((w - tw) // 2, y_pos),
            title,
            fill=(*color, 230),
            font=font_title,
        )
        y_pos += (bbox[3] - bbox[1]) + 8

    if artist:
        bbox = draw.textbbox((0, 0), artist, font=font_artist)
        aw = bbox[2] - bbox[0]
        draw.text(
            ((w - aw) // 2, y_pos),
            artist,
            fill=(255, 255, 255, 180),
            font=font_artist,
        )
