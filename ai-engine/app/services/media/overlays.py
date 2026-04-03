"""Video overlay compositing — provider icons, QR codes, and text wrapping.

Provides functions that accept a numpy frame (H, W, 3) and return a
composited frame with the requested overlay elements burned in.
"""
from __future__ import annotations

import logging
import math
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFont

log = logging.getLogger(__name__)


# ── Default provider icons (SVG-like shapes drawn via Pillow) ───────────────
# These are used when no custom icon file exists.  Each "icon" is rendered as
# a coloured rounded rectangle with a 1-2 letter abbreviation.

DEFAULT_PROVIDERS = {
    "spotify":       {"abbr": "S",  "bg": "#1DB954", "fg": "#fff"},
    "apple_music":   {"abbr": "AM", "bg": "#FA233B", "fg": "#fff"},
    "youtube_music": {"abbr": "YM", "bg": "#FF0000", "fg": "#fff"},
    "tidal":         {"abbr": "T",  "bg": "#000000", "fg": "#fff"},
    "amazon_music":  {"abbr": "AZ", "bg": "#25D1DA", "fg": "#000"},
    "deezer":        {"abbr": "Dz", "bg": "#A238FF", "fg": "#fff"},
    "soundcloud":    {"abbr": "SC", "bg": "#FF5500", "fg": "#fff"},
    "bandcamp":      {"abbr": "BC", "bg": "#1DA0C3", "fg": "#fff"},
    "pandora":       {"abbr": "Pa", "bg": "#224099", "fg": "#fff"},
    "tiktok":        {"abbr": "Tk", "bg": "#010101", "fg": "#69C9D0"},
    "instagram":     {"abbr": "IG", "bg": "#E1306C", "fg": "#fff"},
    "nullrecords":   {"abbr": "NR", "bg": "#6366f1", "fg": "#fff"},
}

# Directory for uploaded custom icon images
ICON_UPLOAD_DIR = Path("exports/provider_icons")


# ── Data classes ────────────────────────────────────────────────────────────

@dataclass
class ProviderIconConfig:
    """Configure the provider icon strip overlay."""
    providers: list[str] = field(default_factory=lambda: list(DEFAULT_PROVIDERS.keys()))
    position: str = "bottom"          # top, bottom, middle
    icon_size: int = 36               # px per icon
    padding: int = 6                  # px between icons
    opacity: float = 0.75             # 0-1 transparency
    margin: int = 20                  # px from edge
    custom_icons: dict[str, str] = field(default_factory=dict)  # name → file path


@dataclass
class QRCodeConfig:
    """Configure the QR code overlay."""
    url: str = "https://www.nullrecords.com"
    position: str = "bottom-right"    # top-left, top-right, bottom-left, bottom-right
    size: int = 80                    # px
    opacity: float = 0.85
    margin: int = 20                  # px from edge
    fg_color: str = "#ffffff"
    bg_color: str = "#00000080"       # semi-transparent black background


# ── Provider icon rendering ─────────────────────────────────────────────────

def _generate_icon(
    abbr: str, bg_hex: str, fg_hex: str, size: int = 36,
) -> Image.Image:
    """Generate a simple rounded-rect icon with abbreviation text."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Parse colors
    bg = _hex_to_rgba(bg_hex)
    fg = _hex_to_rgba(fg_hex)

    # Rounded rectangle background
    radius = size // 5
    draw.rounded_rectangle([(0, 0), (size - 1, size - 1)], radius=radius, fill=bg)

    # Text
    font_size = size // 2 if len(abbr) <= 2 else size // 3
    font = _get_small_font(font_size)
    bbox = draw.textbbox((0, 0), abbr, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (size - tw) // 2
    ty = (size - th) // 2 - 2
    draw.text((tx, ty), abbr, font=font, fill=fg)

    return img


def _load_icon(name: str, size: int, custom_icons: dict[str, str]) -> Image.Image | None:
    """Load an icon — custom file first, then generated fallback."""
    # Check custom uploads
    if name in custom_icons:
        custom_path = Path(custom_icons[name])
        if custom_path.exists():
            try:
                icon = Image.open(str(custom_path)).convert("RGBA")
                return icon.resize((size, size), Image.LANCZOS)
            except Exception as exc:
                log.warning("Failed to load custom icon %s: %s", custom_path, exc)

    # Check icon upload directory
    for ext in (".png", ".svg", ".jpg", ".webp"):
        icon_path = ICON_UPLOAD_DIR / f"{name}{ext}"
        if icon_path.exists():
            try:
                icon = Image.open(str(icon_path)).convert("RGBA")
                return icon.resize((size, size), Image.LANCZOS)
            except Exception as exc:
                log.warning("Failed to load icon %s: %s", icon_path, exc)

    # Generate from defaults
    if name in DEFAULT_PROVIDERS:
        p = DEFAULT_PROVIDERS[name]
        return _generate_icon(p["abbr"], p["bg"], p["fg"], size)

    return None


def render_provider_icons(
    frame: np.ndarray,
    config: ProviderIconConfig,
) -> np.ndarray:
    """Composite provider icon strip onto a video frame.

    Icons are arranged in a horizontal row with padding. If they exceed
    the video width, they wrap to multiple rows.
    """
    fh, fw = frame.shape[:2]
    icon_size = config.icon_size
    pad = config.padding
    margin = config.margin

    # Load all icons
    icons: list[Image.Image] = []
    for name in config.providers:
        icon = _load_icon(name, icon_size, config.custom_icons)
        if icon:
            icons.append(icon)

    if not icons:
        return frame

    # Calculate layout — wrap to multiple rows if needed
    max_per_row = max(1, (fw - 2 * margin + pad) // (icon_size + pad))
    rows: list[list[Image.Image]] = []
    for i in range(0, len(icons), max_per_row):
        rows.append(icons[i:i + max_per_row])

    row_height = icon_size + pad
    total_height = len(rows) * row_height

    # Create the icon strip as RGBA
    strip_w = fw
    strip_h = total_height + margin
    strip = Image.new("RGBA", (strip_w, strip_h), (0, 0, 0, 0))

    # Optional semi-transparent background bar
    bg_alpha = int(config.opacity * 80)  # subtle bg
    bg_draw = ImageDraw.Draw(strip)
    bg_draw.rectangle([(0, 0), (strip_w, strip_h)], fill=(0, 0, 0, bg_alpha))

    # Place icons centered per row
    y_offset = pad // 2
    for row in rows:
        total_row_w = len(row) * icon_size + (len(row) - 1) * pad
        x_start = (strip_w - total_row_w) // 2
        for j, icon in enumerate(row):
            x = x_start + j * (icon_size + pad)
            # Apply per-icon opacity
            if config.opacity < 1.0:
                alpha = icon.split()[3]
                alpha = alpha.point(lambda p: int(p * config.opacity))
                icon.putalpha(alpha)
            strip.paste(icon, (x, y_offset), icon)
        y_offset += row_height

    # Convert strip to numpy and composite onto frame
    strip_arr = np.array(strip)

    # Determine Y position
    if config.position == "top":
        y_pos = margin
    elif config.position == "middle":
        y_pos = (fh - strip_h) // 2
    else:  # bottom
        y_pos = fh - strip_h - margin

    y_pos = max(0, min(y_pos, fh - strip_h))

    return _composite_rgba_onto_frame(frame, strip_arr, 0, y_pos)


# ── QR Code rendering ──────────────────────────────────────────────────────

def generate_qr_image(
    url: str,
    size: int = 80,
    fg_color: str = "#ffffff",
    bg_color: str = "#00000080",
) -> Image.Image:
    """Generate a QR code as an RGBA Pillow image."""
    import qrcode

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=1,
    )
    qr.add_data(url)
    qr.make(fit=True)

    fg_rgb = _hex_to_rgba(fg_color)[:3]
    bg_rgba = _hex_to_rgba(bg_color)

    # Generate with opaque background first
    qr_img = qr.make_image(fill_color=fg_rgb, back_color=bg_rgba[:3])
    qr_img = qr_img.convert("RGBA")

    # Apply background alpha
    data = qr_img.getdata()
    new_data = []
    for item in data:
        # If pixel matches background color, apply bg alpha
        if item[:3] == bg_rgba[:3]:
            new_data.append((*bg_rgba[:3], bg_rgba[3]))
        else:
            new_data.append(item)
    qr_img.putdata(new_data)

    return qr_img.resize((size, size), Image.LANCZOS)


def render_qr_overlay(
    frame: np.ndarray,
    config: QRCodeConfig,
) -> np.ndarray:
    """Composite a QR code onto a video frame."""
    fh, fw = frame.shape[:2]

    qr_img = generate_qr_image(
        url=config.url,
        size=config.size,
        fg_color=config.fg_color,
        bg_color=config.bg_color,
    )

    # Apply opacity
    if config.opacity < 1.0:
        alpha = qr_img.split()[3]
        alpha = alpha.point(lambda p: int(p * config.opacity))
        qr_img.putalpha(alpha)

    qr_arr = np.array(qr_img)
    qr_h, qr_w = qr_arr.shape[:2]
    margin = config.margin

    # Position
    pos = config.position.lower()
    if "left" in pos:
        x = margin
    else:  # right
        x = fw - qr_w - margin

    if "top" in pos:
        y = margin
    else:  # bottom
        y = fh - qr_h - margin

    x = max(0, min(x, fw - qr_w))
    y = max(0, min(y, fh - qr_h))

    return _composite_rgba_onto_frame(frame, qr_arr, x, y)


# ── Text wrapping ───────────────────────────────────────────────────────────

def wrap_text_to_width(
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
    draw: ImageDraw.Draw | None = None,
) -> list[str]:
    """Word-wrap text to fit within max_width pixels using the given font.

    Returns a list of lines that fit within the width.
    """
    if draw is None:
        tmp = Image.new("RGBA", (1, 1))
        draw = ImageDraw.Draw(tmp)

    words = text.split()
    if not words:
        return [text]

    lines = []
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip() if current_line else word
        bbox = draw.textbbox((0, 0), test_line, font=font)
        line_w = bbox[2] - bbox[0]

        if line_w <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            # Handle single word wider than max_width
            bbox_word = draw.textbbox((0, 0), word, font=font)
            if bbox_word[2] - bbox_word[0] > max_width:
                # Force-break long word
                chars = list(word)
                chunk = ""
                for ch in chars:
                    test = chunk + ch
                    bx = draw.textbbox((0, 0), test, font=font)
                    if bx[2] - bx[0] > max_width and chunk:
                        lines.append(chunk)
                        chunk = ch
                    else:
                        chunk = test
                current_line = chunk
            else:
                current_line = word

    if current_line:
        lines.append(current_line)

    return lines if lines else [text]


# ── Composite helper ────────────────────────────────────────────────────────

def _composite_rgba_onto_frame(
    frame: np.ndarray,
    overlay_arr: np.ndarray,
    x: int,
    y: int,
) -> np.ndarray:
    """Alpha-composite an RGBA numpy array onto an RGB frame at (x, y)."""
    result = frame.copy()
    fh, fw = result.shape[:2]
    oh, ow = overlay_arr.shape[:2]

    # Clip to frame bounds
    x2 = min(x + ow, fw)
    y2 = min(y + oh, fh)
    ow_c = x2 - x
    oh_c = y2 - y

    if ow_c <= 0 or oh_c <= 0:
        return result

    alpha = overlay_arr[:oh_c, :ow_c, 3:4].astype(np.float32) / 255.0
    rgb = overlay_arr[:oh_c, :ow_c, :3].astype(np.float32)
    bg = result[y:y2, x:x2].astype(np.float32)

    blended = (rgb * alpha + bg * (1.0 - alpha)).astype(np.uint8)
    result[y:y2, x:x2] = blended

    return result


# ── Font helpers ────────────────────────────────────────────────────────────

def _get_small_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a small font for icon labels."""
    candidates = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSMono.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def _hex_to_rgba(hex_color: str) -> tuple[int, int, int, int]:
    """Parse hex color string to (R, G, B, A) tuple."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    if len(hex_color) == 6:
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        return (r, g, b, 255)
    elif len(hex_color) == 8:
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        a = int(hex_color[6:8], 16)
        return (r, g, b, a)
    return (255, 255, 255, 255)
