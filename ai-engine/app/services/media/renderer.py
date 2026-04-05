"""Video renderer — composes clips into a final vertical short-form video.

Handles clip loading, trimming, resizing, image-to-clip conversion,
text overlay rendering, effect application, concatenation, audio
attachment, and H.264/AAC export.
"""

import logging
import math
import random
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from moviepy import (
    AudioFileClip,
    VideoClip,
    VideoFileClip,
    concatenate_videoclips,
)
from PIL import Image, ImageDraw, ImageFont

from app.services.media.effects import apply_effects_blended, glitch_transition
from app.services.media.overlays import (
    ProviderIconConfig,
    QRCodeConfig,
    render_provider_icons,
    render_qr_overlay,
    wrap_text_to_width,
)

log = logging.getLogger(__name__)

# ── Constants ───────────────────────────────────────────────────────────────
TARGET_FPS = 24
MIN_CLIP_DURATION = 3.0   # seconds
MAX_CLIP_DURATION = 8.0

PRESETS = {
    "vertical": (1080, 1920),   # 9:16 — TikTok/Reels/Shorts
    "widescreen": (1280, 720),  # 16:9 — YouTube landscape (720p)
}

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


# ── Text overlay config ────────────────────────────────────────────────────

@dataclass
class TextOverlay:
    """Defines a text overlay to burn into the video."""
    text: str
    position: str = "center"       # center, top, bottom, lower-third
    font_size: int = 0             # 0 = auto-size
    color: str = "#ffffff"
    shadow: bool = True
    start_sec: float = 0.0         # when to show (0 = immediate)
    end_sec: float = 0.0           # 0 = show for entire video
    font_family: str = ""          # custom font family or path
    text_spacing: int = 0          # line spacing in pixels (0 = auto)


# ── Artwork timing config ──────────────────────────────────────────────────

@dataclass
class ArtworkEntry:
    """One artwork image with timing and animation settings."""
    path: str
    start_sec: float = 0.0         # when this image starts (0 = from beginning)
    duration_sec: float = 0.0      # 0 = auto-fill remaining time
    animation: str = "ken_burns"   # ken_burns, zoom_pulse, rotate, parallax, drift, static
    animation_speed: float = 1.0   # multiplier for animation speed
    crossfade_sec: float = 0.5     # crossfade transition between artworks


# Animation types available for images
ANIMATION_TYPES = [
    "ken_burns",    # Classic slow pan + zoom
    "zoom_pulse",   # Gentle zoom in/out pulsing (syncs with audio if available)
    "rotate",       # Slow rotation around center
    "parallax",     # Layered parallax drift (subtle horizontal shift)
    "drift",        # Slow directional drift (like floating in space)
    "static",       # No animation (useful for complex artwork)
]


def render_video(
    clip_paths: list[Path],
    audio_path: Path | None,
    output_path: Path,
    fps: int = TARGET_FPS,
    use_glitch_transitions: bool = True,
    aspect: str = "vertical",
    image_paths: list[Path] | None = None,
    text_overlays: list[TextOverlay] | None = None,
    effect_config=None,
    visualizer_config: dict | None = None,
    audio_data: dict | None = None,
    artwork_entries: list[ArtworkEntry] | None = None,
    target_duration_sec: float = 0.0,
    provider_icon_config: ProviderIconConfig | None = None,
    qr_code_config: QRCodeConfig | None = None,
) -> Path:
    """Render a short-form video from clips, images, text overlays, visualizer + audio.

    When artwork_entries is provided, artwork images form a persistent background
    layer with effects and visualizer overlaid transparently on top. Each artwork
    can have its own animation style and display timing.

    Steps:
        1. Convert images to animated clips (Ken Burns or other animations).
        2. Load each video clip.
        3. Trim to 3–8 seconds.
        4. Resize to target aspect.
        5. Apply cinematic effects (with configurable opacity/types).
        6. Concatenate (with optional glitch transitions at configurable opacity).
        7. Trim or extend final video to match target duration (audio sync).
        8. Apply text overlays.
        9. Composite EQ visualizer overlay (if enabled).
        10. Apply beat flash (if enabled + audio analyzed).
        11. Attach audio track.
        12. Export H.264 / AAC.
    """
    target_w, target_h = PRESETS.get(aspect, PRESETS["vertical"])
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Determine target duration from audio if not explicitly set
    audio_duration = 0.0
    if audio_path and audio_path.exists():
        try:
            ac = AudioFileClip(str(audio_path))
            audio_duration = ac.duration
            ac.close()
        except Exception:
            pass
    if target_duration_sec > 0:
        final_target_dur = target_duration_sec
    elif audio_duration > 0:
        final_target_dur = audio_duration
    else:
        final_target_dur = 0  # no target — use natural clip length

    # ── ARTWORK MODE: persistent background with overlays ───────────────
    if artwork_entries:
        log.info(
            "Artwork mode: %d artworks → %s (%s %dx%d, target %.1fs)",
            len(artwork_entries), output_path.name, aspect, target_w, target_h,
            final_target_dur,
        )
        final_video = _render_artwork_sequence(
            artwork_entries, target_w, target_h, final_target_dur, fps, effect_config,
        )
    else:
        # ── LEGACY MODE: interleaved clips + images ─────────────────────
        all_sources = list(clip_paths or []) + list(image_paths or [])
        if not all_sources:
            raise ValueError("No clip or image paths provided")

        log.info(
            "Rendering video: %d clips + %d images → %s (%s %dx%d)",
            len(clip_paths or []), len(image_paths or []),
            output_path.name, aspect, target_w, target_h,
        )

        # ── 1. Convert images to animated clips ─────────────────────────
        image_clips: list = []
        for img_path in (image_paths or []):
            log.info("  Converting image → clip: %s", img_path.name)
            try:
                ic = _image_to_clip(img_path, target_w, target_h, fps=fps, effect_config=effect_config)
                image_clips.append(ic)
            except Exception as exc:
                log.warning("  Skipping image %s — %s", img_path.name, exc)

        # ── 2. Load & prepare video clips ───────────────────────────────
        video_clips: list = []
        for i, cp in enumerate(clip_paths or []):
            log.info("  [%d/%d] Loading video %s", i + 1, len(clip_paths or []), cp.name)
            try:
                raw = VideoFileClip(str(cp))
            except Exception as exc:
                log.warning("  Skipping %s — failed to load: %s", cp.name, exc)
                continue

            trimmed = _trim_clip(raw)
            resized = _resize_clip(trimmed, target_w, target_h)
            with_fx = apply_effects_blended(resized, config=effect_config)
            video_clips.append(with_fx)

        # ── 3. Interleave images and video clips ────────────────────────
        prepared = _interleave(image_clips, video_clips)

        if not prepared:
            raise RuntimeError("No clips could be loaded — cannot render video")

        # ── 4. Concatenate ──────────────────────────────────────────────
        if use_glitch_transitions and len(prepared) > 1:
            glitch_opacity = effect_config.glitch_opacity if effect_config else 1.0
            final_video = _concat_with_glitch(prepared, opacity=glitch_opacity)
        else:
            final_video = concatenate_videoclips(prepared, method="compose")

    # ── Duration sync: trim or extend to match audio ────────────────────
    if final_target_dur > 0 and final_video.duration:
        if final_video.duration > final_target_dur + 0.5:
            log.info("Trimming video %.1fs → %.1fs to match audio", final_video.duration, final_target_dur)
            final_video = final_video.subclipped(0, final_target_dur)
        elif not artwork_entries and final_video.duration < final_target_dur - 0.5:
            # Legacy mode only: extend by looping the full video
            deficit = final_target_dur - final_video.duration
            loops = math.ceil(final_target_dur / final_video.duration)
            log.info("Looping video %dx to fill %.1fs (was %.1fs)", loops, final_target_dur, final_video.duration)
            looped = concatenate_videoclips([final_video] * loops, method="compose")
            final_video = looped.subclipped(0, final_target_dur)

    # ── 5. Text overlays ────────────────────────────────────────────────
    if text_overlays:
        final_video = _apply_text_overlays(final_video, text_overlays, target_w, target_h)

    # ── 5b. Provider icon strip ─────────────────────────────────────────
    if provider_icon_config:
        log.info(
            "Adding provider icons (%d providers, position=%s)",
            len(provider_icon_config.providers), provider_icon_config.position,
        )
        final_video = _apply_frame_overlay(
            final_video, lambda frame: render_provider_icons(frame, provider_icon_config),
        )

    # ── 5c. QR code overlay ─────────────────────────────────────────────
    if qr_code_config:
        log.info("Adding QR code → %s (position=%s)", qr_code_config.url, qr_code_config.position)
        final_video = _apply_frame_overlay(
            final_video, lambda frame: render_qr_overlay(frame, qr_code_config),
        )

    # ── 6. EQ Visualizer overlay ────────────────────────────────────────
    if visualizer_config:
        log.info("Compositing EQ visualizer (%s)", visualizer_config.get("type", "bars"))
        final_video = _apply_visualizer(final_video, visualizer_config, fps)

    # ── 7. Beat flash ───────────────────────────────────────────────────
    if audio_data and effect_config and effect_config.beat_flash_enabled:
        from app.services.media.effects import beat_flash_effect
        beats = audio_data.get("beats", [])
        if beats:
            log.info("Applying beat flash (%d beats)", len(beats))
            final_video = beat_flash_effect(
                final_video, beats,
                intensity=effect_config.beat_flash_intensity,
            )

    # ── 8. Attach audio ─────────────────────────────────────────────────
    if audio_path and audio_path.exists():
        log.info("Attaching audio: %s", audio_path.name)
        audio_clip = AudioFileClip(str(audio_path))
        if audio_clip.duration > final_video.duration:
            audio_clip = audio_clip.subclipped(0, final_video.duration)
        final_video = final_video.with_audio(audio_clip)
    else:
        log.info("No audio — rendering silent video")

    # ── 9. Export ────────────────────────────────────────────────────────
    log.info(
        "Exporting video: %s (%.1fs, %dx%d @ %dfps)",
        output_path.name, final_video.duration,
        final_video.w, final_video.h, fps,
    )

    # Use CRF 18 for high quality; widescreen gets higher bitrate floor
    ffmpeg_params = ["-crf", "18", "-pix_fmt", "yuv420p"]
    if aspect == "widescreen":
        ffmpeg_params += ["-b:v", "4M", "-maxrate", "6M", "-bufsize", "8M"]
    else:
        ffmpeg_params += ["-b:v", "5M", "-maxrate", "8M", "-bufsize", "10M"]

    final_video.write_videofile(
        str(output_path),
        fps=fps,
        codec="libx264",
        audio_codec="aac",
        audio_bitrate="192k",
        preset="medium",
        threads=4,
        ffmpeg_params=ffmpeg_params,
        logger=None,
    )

    # Cleanup
    final_video.close()
    if not artwork_entries:
        for c in prepared:
            try:
                c.close()
            except Exception:
                pass

    log.info("✓ Video rendered: %s (%.1f KB)", output_path.name, output_path.stat().st_size / 1024)
    return output_path


def render_preview_frame(
    image_path: Path | None = None,
    clip_path: Path | None = None,
    text_overlays: list[TextOverlay] | None = None,
    effect_config=None,
    visualizer_config: dict | None = None,
    aspect: str = "vertical",
    time_sec: float = 2.0,
    fps: int = TARGET_FPS,
) -> np.ndarray:
    """Render a single preview frame (no video encoding).

    Returns an RGB numpy array (H, W, 3) uint8 suitable for saving as PNG.
    Shows what the video will look like at the given timestamp.
    """
    target_w, target_h = PRESETS.get(aspect, PRESETS["vertical"])

    # Get a base frame from image or clip
    frame = None

    if image_path and image_path.exists():
        img = Image.open(str(image_path)).convert("RGB")
        # Upscale small images
        min_dim = max(target_w, target_h) * 2
        if img.width < min_dim or img.height < min_dim:
            scale = min_dim / min(img.width, img.height)
            img = img.resize(
                (int(img.width * scale), int(img.height * scale)),
                Image.LANCZOS,
            )
        img_arr = np.array(img)
        img_h, img_w = img_arr.shape[:2]

        # Simulate Ken Burns at time_sec (simple center crop + slight zoom)
        zoom = 0.55  # mid-range zoom
        crop_w = int(img_w * zoom)
        crop_h = int(crop_w * target_h / target_w)
        if crop_h > img_h:
            crop_h = img_h
            crop_w = int(crop_h * target_w / target_h)
        x1 = (img_w - crop_w) // 2
        y1 = (img_h - crop_h) // 2
        cropped = img_arr[y1:y1+crop_h, x1:x1+crop_w]
        pil_resized = Image.fromarray(cropped).resize((target_w, target_h), Image.LANCZOS)
        frame = np.array(pil_resized)

    elif clip_path and clip_path.exists():
        try:
            raw = VideoFileClip(str(clip_path))
            t = min(time_sec, raw.duration - 0.1)
            frame = raw.get_frame(max(0, t))
            raw.close()
            # Resize to target
            pil_frame = Image.fromarray(frame)
            # Crop to fill
            fw, fh = pil_frame.size
            target_ratio = target_w / target_h
            src_ratio = fw / fh
            if src_ratio > target_ratio:
                new_w = int(fh * target_ratio)
                x_off = (fw - new_w) // 2
                pil_frame = pil_frame.crop((x_off, 0, x_off + new_w, fh))
            else:
                new_h = int(fw / target_ratio)
                y_off = (fh - new_h) // 2
                pil_frame = pil_frame.crop((0, y_off, fw, y_off + new_h))
            pil_frame = pil_frame.resize((target_w, target_h), Image.LANCZOS)
            frame = np.array(pil_frame)
        except Exception as exc:
            log.warning("Could not load clip for preview: %s", exc)

    if frame is None:
        # Fallback: dark placeholder
        frame = np.full((target_h, target_w, 3), 15, dtype=np.uint8)

    # Apply effects as transparent overlay
    if effect_config:
        from app.services.media.effects import EffectConfig, apply_effects_blended
        # Create a temporary 1-frame clip to apply effects
        duration = 0.1
        base_frame = frame.copy()

        def _make_frame(t):
            return base_frame

        tmp_clip = VideoClip(_make_frame, duration=duration).with_fps(fps)
        effected_clip = apply_effects_blended(tmp_clip, config=effect_config)
        frame = effected_clip.get_frame(0)
        tmp_clip.close()
        effected_clip.close()

    # Apply text overlays
    if text_overlays:
        # Render text directly onto the frame using Pillow
        base_img = Image.fromarray(frame).convert("RGBA")

        for ov in text_overlays:
            font_size = ov.font_size or max(32, target_w // 18)
            font = _get_font(font_size, family=ov.font_family)
            color = _hex_to_rgb(ov.color)
            spacing = ov.text_spacing if ov.text_spacing > 0 else 8

            tmp_img = Image.new("RGBA", (1, 1))
            draw = ImageDraw.Draw(tmp_img)

            # Word-wrap text to fit video width
            pad = 20
            max_text_w = int(target_w * 0.85) - pad * 2
            raw_lines = ov.text.split("\\n") if "\\n" in ov.text else [ov.text]
            lines = []
            for raw_line in raw_lines:
                wrapped = wrap_text_to_width(raw_line, font, max_text_w, draw)
                lines.extend(wrapped)

            line_bboxes = []
            total_h = 0
            max_w = 0
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                lw = bbox[2] - bbox[0]
                lh = bbox[3] - bbox[1]
                line_bboxes.append((lw, lh))
                total_h += lh + spacing
                max_w = max(max_w, lw)

            pad = 20
            ow = max_w + pad * 2
            oh = total_h + pad * 2

            overlay_img = Image.new("RGBA", (ow, oh), (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay_img)

            y_cursor = pad
            for i, line in enumerate(lines):
                lw, lh = line_bboxes[i]
                x = (ow - lw) // 2
                if ov.shadow:
                    overlay_draw.text((x + 2, y_cursor + 2), line, font=font, fill=(0, 0, 0, 200))
                    overlay_draw.text((x + 1, y_cursor + 1), line, font=font, fill=(0, 0, 0, 140))
                overlay_draw.text((x, y_cursor), line, font=font, fill=(*color, 255))
                y_cursor += lh + spacing

            # Position
            if ov.position == "top":
                pos_x = (target_w - ow) // 2
                pos_y = int(target_h * 0.06)
            elif ov.position == "bottom":
                pos_x = (target_w - ow) // 2
                pos_y = int(target_h * 0.85)
            elif ov.position == "lower-third":
                pos_x = (target_w - ow) // 2
                pos_y = int(target_h * 0.72)
            else:
                pos_x = (target_w - ow) // 2
                pos_y = (target_h - oh) // 2

            base_img.paste(overlay_img, (max(0, pos_x), max(0, pos_y)), overlay_img)

        frame = np.array(base_img.convert("RGB"))

    # Apply visualizer overlay
    if visualizer_config:
        from app.services.media.visualizer import render_visualizer_frame
        frame_idx = int(time_sec * fps)
        frame = render_visualizer_frame(frame, frame_idx, visualizer_config)

    return frame


# ── Image → animated clip ───────────────────────────────────────────────────

def _image_to_clip(
    image_path: Path,
    target_w: int,
    target_h: int,
    duration: float = 0.0,
    fps: int = TARGET_FPS,
    effect_config=None,
) -> VideoClip:
    """Convert a still image into an animated video clip with Ken Burns effect.

    Loads the image at high resolution, then slowly pans and zooms
    across it to create cinematic motion from a still photo.
    """
    if duration <= 0:
        duration = random.uniform(MIN_CLIP_DURATION, MAX_CLIP_DURATION)

    img = Image.open(str(image_path)).convert("RGB")

    # Upscale small images so we have room for pan/zoom
    min_dim = max(target_w, target_h) * 2
    if img.width < min_dim or img.height < min_dim:
        scale = min_dim / min(img.width, img.height)
        img = img.resize(
            (int(img.width * scale), int(img.height * scale)),
            Image.LANCZOS,
        )

    img_arr = np.array(img)
    img_h, img_w = img_arr.shape[:2]

    # Choose random pan direction
    directions = ["zoom_in", "zoom_out", "pan_left", "pan_right", "pan_up", "pan_down"]
    direction = random.choice(directions)

    # Zoom range: start_zoom to end_zoom (fraction of image visible)
    if direction == "zoom_in":
        start_z, end_z = 0.7, 0.45
        start_cx, start_cy = 0.5, 0.5
        end_cx, end_cy = 0.5, 0.5
    elif direction == "zoom_out":
        start_z, end_z = 0.45, 0.7
        start_cx, start_cy = 0.5, 0.5
        end_cx, end_cy = 0.5, 0.5
    elif direction == "pan_left":
        start_z = end_z = 0.55
        start_cx, end_cx = 0.65, 0.35
        start_cy = end_cy = 0.5
    elif direction == "pan_right":
        start_z = end_z = 0.55
        start_cx, end_cx = 0.35, 0.65
        start_cy = end_cy = 0.5
    elif direction == "pan_up":
        start_z = end_z = 0.55
        start_cx = end_cx = 0.5
        start_cy, end_cy = 0.6, 0.4
    else:  # pan_down
        start_z = end_z = 0.55
        start_cx = end_cx = 0.5
        start_cy, end_cy = 0.4, 0.6

    def make_frame(t):
        progress = t / duration if duration > 0 else 0
        # Smooth ease-in-out
        progress = 0.5 - 0.5 * math.cos(math.pi * progress)

        zoom = start_z + (end_z - start_z) * progress
        cx = start_cx + (end_cx - start_cx) * progress
        cy = start_cy + (end_cy - start_cy) * progress

        # Compute crop window at current zoom level
        crop_w = int(img_w * zoom)
        crop_h = int(crop_w * target_h / target_w)

        # Clamp crop dimensions
        if crop_h > img_h:
            crop_h = img_h
            crop_w = int(crop_h * target_w / target_h)

        x1 = int(cx * img_w - crop_w / 2)
        y1 = int(cy * img_h - crop_h / 2)
        x1 = max(0, min(x1, img_w - crop_w))
        y1 = max(0, min(y1, img_h - crop_h))

        cropped = img_arr[y1 : y1 + crop_h, x1 : x1 + crop_w]
        # Resize to target
        pil_crop = Image.fromarray(cropped)
        pil_resized = pil_crop.resize((target_w, target_h), Image.LANCZOS)
        return np.array(pil_resized)

    clip = VideoClip(make_frame, duration=duration).with_fps(fps)
    # Apply cinematic effects (grain, flicker) on image clips too
    clip = apply_effects_blended(clip, config=effect_config)
    log.info("    Image clip: %s → %.1fs (%s)", image_path.name, duration, direction)
    return clip


# ── Text overlay ────────────────────────────────────────────────────────────

def _get_font(size: int, family: str = "") -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Try to load a good font, fall back to default."""
    # If a custom family was specified, try it first
    if family:
        custom_candidates = [
            family,  # direct path or system name
            f"/System/Library/Fonts/{family}.ttc",
            f"/System/Library/Fonts/{family}.ttf",
            f"/System/Library/Fonts/Supplemental/{family}.ttf",
            f"/usr/share/fonts/truetype/{family.lower()}/{family}.ttf",
        ]
        for path in custom_candidates:
            try:
                return ImageFont.truetype(path, size)
            except (OSError, IOError):
                continue

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


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def _apply_text_overlays(
    clip: VideoClip,
    overlays: list[TextOverlay],
    target_w: int,
    target_h: int,
) -> VideoClip:
    """Burn text overlays into the video using Pillow rendering."""
    if not overlays:
        return clip

    # Pre-render each overlay's text image (RGBA with transparency)
    rendered_overlays = []
    for ov in overlays:
        font_size = ov.font_size or max(32, target_w // 18)
        font = _get_font(font_size, family=ov.font_family)
        color = _hex_to_rgb(ov.color)
        spacing = ov.text_spacing if ov.text_spacing > 0 else 8

        # Measure text with word-wrapping to fit video width
        tmp_img = Image.new("RGBA", (1, 1))
        draw = ImageDraw.Draw(tmp_img)

        # Max text width = 85% of video width, minus padding
        pad = 20
        max_text_w = int(target_w * 0.85) - pad * 2

        # Split on explicit newlines first, then word-wrap each line
        raw_lines = ov.text.split("\\n") if "\\n" in ov.text else [ov.text]
        lines = []
        for raw_line in raw_lines:
            wrapped = wrap_text_to_width(raw_line, font, max_text_w, draw)
            lines.extend(wrapped)

        line_bboxes = []
        total_h = 0
        max_w = 0
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            lw = bbox[2] - bbox[0]
            lh = bbox[3] - bbox[1]
            line_bboxes.append((lw, lh))
            total_h += lh + spacing
            max_w = max(max_w, lw)

        # Padding
        pad = 20
        overlay_w = max_w + pad * 2
        overlay_h = total_h + pad * 2

        # Draw text overlay image (no background — clean text with shadow)
        overlay_img = Image.new("RGBA", (overlay_w, overlay_h), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay_img)

        y_cursor = pad
        for i, line in enumerate(lines):
            lw, lh = line_bboxes[i]
            x = (overlay_w - lw) // 2

            # Shadow for readability
            if ov.shadow:
                overlay_draw.text((x + 2, y_cursor + 2), line, font=font, fill=(0, 0, 0, 200))
                overlay_draw.text((x + 1, y_cursor + 1), line, font=font, fill=(0, 0, 0, 140))

            overlay_draw.text((x, y_cursor), line, font=font, fill=(*color, 255))
            y_cursor += lh + spacing

        overlay_arr = np.array(overlay_img)

        # Compute position
        if ov.position == "top":
            pos_x = (target_w - overlay_w) // 2
            pos_y = int(target_h * 0.06)
        elif ov.position == "bottom":
            pos_x = (target_w - overlay_w) // 2
            pos_y = int(target_h * 0.85)
        elif ov.position == "lower-third":
            pos_x = (target_w - overlay_w) // 2
            pos_y = int(target_h * 0.72)
        else:  # center
            pos_x = (target_w - overlay_w) // 2
            pos_y = (target_h - overlay_h) // 2

        rendered_overlays.append({
            "arr": overlay_arr,
            "x": max(0, pos_x),
            "y": max(0, pos_y),
            "start": ov.start_sec,
            "end": ov.end_sec,
        })

    def _composite_frame(get_frame, t):
        frame = get_frame(t).copy()
        fh, fw = frame.shape[:2]

        for rov in rendered_overlays:
            # Check time window
            if rov["start"] > 0 and t < rov["start"]:
                continue
            if rov["end"] > 0 and t > rov["end"]:
                continue

            oa = rov["arr"]
            oh, ow = oa.shape[:2]
            x, y = rov["x"], rov["y"]

            # Clamp to frame bounds
            x2 = min(x + ow, fw)
            y2 = min(y + oh, fh)
            ow_c = x2 - x
            oh_c = y2 - y

            if ow_c <= 0 or oh_c <= 0:
                continue

            alpha = oa[:oh_c, :ow_c, 3:4].astype(np.float32) / 255.0
            rgb = oa[:oh_c, :ow_c, :3].astype(np.float32)
            bg = frame[y:y2, x:x2].astype(np.float32)

            blended = (rgb * alpha + bg * (1.0 - alpha)).astype(np.uint8)
            frame[y:y2, x:x2] = blended

        return frame

    return clip.transform(_composite_frame)


# ── Internal helpers ────────────────────────────────────────────────────────

def _trim_clip(clip: VideoFileClip) -> VideoFileClip:
    """Trim clip to 3–8 seconds, picking a random window if longer."""
    duration = clip.duration or 0
    if duration <= 0:
        return clip

    target = random.uniform(MIN_CLIP_DURATION, MAX_CLIP_DURATION)
    if duration <= target:
        return clip

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
        return clip.resized((target_w, target_h))

    if src_ratio > target_ratio:
        new_w = int(h * target_ratio)
        x_offset = (w - new_w) // 2
        cropped = clip.cropped(x1=x_offset, x2=x_offset + new_w)
    else:
        new_h = int(w / target_ratio)
        y_offset = (h - new_h) // 2
        cropped = clip.cropped(y1=y_offset, y2=y_offset + new_h)

    return cropped.resized((target_w, target_h))


def _interleave(image_clips: list, video_clips: list) -> list:
    """Interleave image and video clips for visual variety.

    If both are present, alternates image-video-image-video...
    starting with an image for a strong visual opening.
    """
    if not image_clips:
        return video_clips
    if not video_clips:
        return image_clips

    result = []
    vi = 0
    ii = 0
    use_image = True  # Start with an image for visual impact

    while ii < len(image_clips) or vi < len(video_clips):
        if use_image and ii < len(image_clips):
            result.append(image_clips[ii])
            ii += 1
        elif vi < len(video_clips):
            result.append(video_clips[vi])
            vi += 1
        elif ii < len(image_clips):
            result.append(image_clips[ii])
            ii += 1
        use_image = not use_image

    return result


def _concat_with_glitch(clips: list, opacity: float = 1.0) -> VideoFileClip:
    """Concatenate clips with glitch transitions between each pair."""
    if len(clips) == 1:
        return clips[0]

    result = clips[0]
    for i in range(1, len(clips)):
        result = glitch_transition(result, clips[i], glitch_duration=0.25, opacity=opacity)

    return result


def _apply_frame_overlay(clip: VideoClip, overlay_fn) -> VideoClip:
    """Apply a per-frame overlay function to every frame of a clip.

    overlay_fn receives an RGB numpy array and returns a modified RGB array.
    """
    def _transform(get_frame, t):
        frame = get_frame(t)
        return overlay_fn(frame)

    return clip.transform(_transform)


def _apply_visualizer(clip: VideoClip, viz_config: dict, fps: int) -> VideoClip:
    """Composite the EQ visualizer onto every frame of the clip."""
    from app.services.media.visualizer import render_visualizer_frame

    def _viz_frame(get_frame, t):
        frame = get_frame(t)
        frame_idx = int(t * fps)
        return render_visualizer_frame(frame, frame_idx, viz_config)

    return clip.transform(_viz_frame)


# ── Artwork sequence renderer ───────────────────────────────────────────────

def _render_artwork_sequence(
    entries: list[ArtworkEntry],
    target_w: int,
    target_h: int,
    total_duration: float,
    fps: int,
    effect_config=None,
) -> VideoClip:
    """Render a sequence of artwork images as a continuous video.

    Each ArtworkEntry specifies its own animation type, timing, and crossfade.
    Effects/visualizer are composited later by the caller — this function
    produces the clean animated artwork background.
    """
    if not entries:
        raise ValueError("No artwork entries provided")

    # Load and prepare all images
    prepared = []
    for entry in entries:
        try:
            img = Image.open(entry.path).convert("RGB")
            # Upscale small images for animation headroom
            min_dim = max(target_w, target_h) * 2
            if img.width < min_dim or img.height < min_dim:
                scale = min_dim / min(img.width, img.height)
                img = img.resize(
                    (int(img.width * scale), int(img.height * scale)),
                    Image.LANCZOS,
                )
            prepared.append({"entry": entry, "img": np.array(img)})
        except Exception as exc:
            log.warning("Skipping artwork %s: %s", entry.path, exc)

    if not prepared:
        raise RuntimeError("No artwork images could be loaded")

    # Auto-fill durations for entries with duration_sec=0
    _assign_artwork_durations(prepared, total_duration)

    # Build a clip for each artwork
    artwork_clips = []
    for item in prepared:
        entry = item["entry"]
        img_arr = item["img"]
        dur = entry.duration_sec

        if dur <= 0:
            continue

        animation_fn = _get_animation_fn(entry.animation)
        clip = _animated_artwork_clip(
            img_arr, target_w, target_h, dur, fps,
            animation_fn, entry.animation_speed,
        )
        artwork_clips.append({"clip": clip, "crossfade": entry.crossfade_sec})
        log.info(
            "  Artwork: %s → %.1fs (%s, speed=%.1f)",
            Path(entry.path).name, dur, entry.animation, entry.animation_speed,
        )

    if not artwork_clips:
        raise RuntimeError("No artwork clips produced")

    # Build one pass of the artwork sequence with crossfades
    def _concat_artwork_pass(clips_list):
        """Concatenate a list of artwork clip dicts with crossfades."""
        if len(clips_list) == 1:
            return clips_list[0]["clip"]
        result = clips_list[0]["clip"]
        for i in range(1, len(clips_list)):
            xfade = min(clips_list[i]["crossfade"], 1.0)
            next_clip = clips_list[i]["clip"]
            if xfade > 0 and result.duration > xfade and next_clip.duration > xfade:
                result = _crossfade_clips(result, next_clip, xfade, fps)
            else:
                result = concatenate_videoclips([result, next_clip], method="compose")
        return result

    one_pass = _concat_artwork_pass(artwork_clips)
    one_pass_dur = one_pass.duration

    # Loop artwork sequence to fill the full target duration
    if total_duration > 0 and one_pass_dur < total_duration - 0.1:
        loops_needed = math.ceil(total_duration / one_pass_dur)
        log.info(
            "Artwork sequence %.1fs < target %.1fs — looping %dx (with animations)",
            one_pass_dur, total_duration, loops_needed,
        )

        # Rebuild animated clips for each loop pass (fresh animations)
        all_passes = [one_pass]
        for loop_idx in range(1, loops_needed):
            loop_clips = []
            for item in prepared:
                entry = item["entry"]
                img_arr = item["img"]
                dur = entry.duration_sec
                if dur <= 0:
                    continue
                animation_fn = _get_animation_fn(entry.animation)
                clip = _animated_artwork_clip(
                    img_arr, target_w, target_h, dur, fps,
                    animation_fn, entry.animation_speed,
                )
                loop_clips.append({"clip": clip, "crossfade": entry.crossfade_sec})

            if loop_clips:
                loop_pass = _concat_artwork_pass(loop_clips)
                # Crossfade between loop passes for seamless transition
                xfade = min(loop_clips[0]["crossfade"], 1.0) if loop_clips[0]["crossfade"] > 0 else 0.5
                prev = all_passes[-1]
                if xfade > 0 and prev.duration > xfade and loop_pass.duration > xfade:
                    merged = _crossfade_clips(prev, loop_pass, xfade, fps)
                    all_passes[-1] = merged
                else:
                    all_passes.append(loop_pass)

        if len(all_passes) == 1:
            final = all_passes[0]
        else:
            final = concatenate_videoclips(all_passes, method="compose")

        # Trim to exact target duration
        if final.duration > total_duration + 0.1:
            final = final.subclipped(0, total_duration)
    else:
        final = one_pass

    # Apply effects as a transparent overlay (low opacity to preserve artwork)
    if effect_config:
        final = apply_effects_blended(final, config=effect_config)

    return final


def _assign_artwork_durations(prepared: list[dict], total_duration: float):
    """Assign durations to artwork entries that have duration_sec=0 (auto).

    Ensures total artwork duration always covers the full video.
    """
    fixed_time = sum(
        item["entry"].duration_sec for item in prepared if item["entry"].duration_sec > 0
    )
    auto_count = sum(1 for item in prepared if item["entry"].duration_sec <= 0)

    if auto_count > 0:
        remaining = max(0, total_duration - fixed_time) if total_duration > 0 else 10.0 * auto_count
        per_auto = remaining / auto_count if auto_count > 0 else 5.0
        for item in prepared:
            if item["entry"].duration_sec <= 0:
                item["entry"].duration_sec = max(2.0, per_auto)

    # Only extend the last entry if there were auto-duration entries.
    # When all entries have explicit durations, let the looping code handle gaps.
    if auto_count > 0:
        total_artwork = sum(item["entry"].duration_sec for item in prepared)
        total_crossfades = sum(
            min(item["entry"].crossfade_sec, 1.0)
            for item in prepared[1:]
        )
        effective_duration = total_artwork - total_crossfades

        if total_duration > 0 and effective_duration < total_duration:
            deficit = total_duration - effective_duration
            prepared[-1]["entry"].duration_sec += deficit + 0.5
            log.info(
                "Extended last artwork by %.1fs to fill video duration (%.1fs total)",
                deficit + 0.5, total_duration,
            )


def _get_animation_fn(animation_type: str):
    """Return the animation function for a given type name."""
    animations = {
        "ken_burns": _anim_ken_burns,
        "zoom_pulse": _anim_zoom_pulse,
        "rotate": _anim_rotate,
        "parallax": _anim_parallax,
        "drift": _anim_drift,
        "static": _anim_static,
    }
    return animations.get(animation_type, _anim_ken_burns)


def _animated_artwork_clip(
    img_arr: np.ndarray,
    target_w: int,
    target_h: int,
    duration: float,
    fps: int,
    animation_fn,
    speed: float = 1.0,
) -> VideoClip:
    """Create a video clip from an image array with the specified animation."""
    img_h, img_w = img_arr.shape[:2]

    def make_frame(t):
        return animation_fn(img_arr, img_w, img_h, target_w, target_h, t, duration, speed)

    return VideoClip(make_frame, duration=duration).with_fps(fps)


def _crossfade_clips(clip_a: VideoClip, clip_b: VideoClip, xfade_dur: float, fps: int) -> VideoClip:
    """Crossfade between two clips by blending the overlap region."""
    dur_a = clip_a.duration
    dur_b = clip_b.duration
    total = dur_a + dur_b - xfade_dur

    def make_frame(t):
        if t < dur_a - xfade_dur:
            return clip_a.get_frame(t)
        elif t >= dur_a:
            return clip_b.get_frame(t - dur_a + xfade_dur)
        else:
            # In the crossfade zone
            progress = (t - (dur_a - xfade_dur)) / xfade_dur
            progress = max(0.0, min(1.0, progress))
            frame_a = clip_a.get_frame(t).astype(np.float32)
            frame_b = clip_b.get_frame(t - dur_a + xfade_dur).astype(np.float32)
            blended = (frame_a * (1.0 - progress) + frame_b * progress).astype(np.uint8)
            return blended

    return VideoClip(make_frame, duration=total).with_fps(fps)


# ── Animation functions ─────────────────────────────────────────────────────
# Each takes: img_arr, img_w, img_h, target_w, target_h, t, duration, speed
# Returns: np.ndarray (target_h, target_w, 3) uint8

def _crop_and_resize(img_arr, img_w, img_h, target_w, target_h, cx, cy, zoom):
    """Helper: crop from image at (cx, cy) with zoom level, resize to target."""
    crop_w = int(img_w * zoom)
    crop_h = int(crop_w * target_h / target_w)
    if crop_h > img_h:
        crop_h = img_h
        crop_w = int(crop_h * target_w / target_h)
    x1 = int(cx * img_w - crop_w / 2)
    y1 = int(cy * img_h - crop_h / 2)
    x1 = max(0, min(x1, img_w - crop_w))
    y1 = max(0, min(y1, img_h - crop_h))
    cropped = img_arr[y1:y1 + crop_h, x1:x1 + crop_w]
    pil_resized = Image.fromarray(cropped).resize((target_w, target_h), Image.LANCZOS)
    return np.array(pil_resized)


def _ease(t_norm):
    """Smooth ease-in-out."""
    return 0.5 - 0.5 * math.cos(math.pi * t_norm)


def _anim_ken_burns(img_arr, img_w, img_h, tw, th, t, dur, speed):
    """Classic slow pan + zoom."""
    p = _ease(min(1.0, t * speed / dur))
    # Zoom from 0.7 to 0.45 while panning slightly
    zoom = 0.7 - 0.25 * p
    cx = 0.45 + 0.1 * p
    cy = 0.45 + 0.1 * p
    return _crop_and_resize(img_arr, img_w, img_h, tw, th, cx, cy, zoom)


def _anim_zoom_pulse(img_arr, img_w, img_h, tw, th, t, dur, speed):
    """Gentle zoom in/out pulsing — great for music sync."""
    cycle = 2.0 / speed  # pulse period in seconds
    phase = (t % cycle) / cycle
    pulse = 0.5 + 0.5 * math.sin(2 * math.pi * phase)
    zoom = 0.5 + 0.1 * pulse  # oscillates 0.5–0.6
    return _crop_and_resize(img_arr, img_w, img_h, tw, th, 0.5, 0.5, zoom)


def _anim_rotate(img_arr, img_w, img_h, tw, th, t, dur, speed):
    """Slow rotation around center with slight zoom."""
    angle = t * speed * 15  # degrees per second
    zoom = 0.5
    # Rotate the image using PIL
    pil_img = Image.fromarray(img_arr)
    rotated = pil_img.rotate(-angle, resample=Image.BICUBIC, expand=False)
    rot_arr = np.array(rotated)
    return _crop_and_resize(rot_arr, img_w, img_h, tw, th, 0.5, 0.5, zoom)


def _anim_parallax(img_arr, img_w, img_h, tw, th, t, dur, speed):
    """Layered parallax drift — subtle horizontal shift."""
    p = _ease(min(1.0, t * speed / dur))
    cx = 0.3 + 0.4 * p  # drift from left to right
    zoom = 0.55
    return _crop_and_resize(img_arr, img_w, img_h, tw, th, cx, 0.5, zoom)


def _anim_drift(img_arr, img_w, img_h, tw, th, t, dur, speed):
    """Slow floating drift — diagonal movement like drifting in space."""
    p = min(1.0, t * speed / dur)
    # Smooth sinusoidal path
    cx = 0.4 + 0.2 * math.sin(p * math.pi)
    cy = 0.4 + 0.2 * math.cos(p * math.pi * 0.7)
    zoom = 0.5 + 0.05 * math.sin(p * math.pi * 2)
    return _crop_and_resize(img_arr, img_w, img_h, tw, th, cx, cy, zoom)


def _anim_static(img_arr, img_w, img_h, tw, th, t, dur, speed):
    """No animation — center crop at fixed zoom."""
    return _crop_and_resize(img_arr, img_w, img_h, tw, th, 0.5, 0.5, 0.55)
