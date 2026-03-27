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
) -> Path:
    """Render a short-form video from clips, images, text overlays, visualizer + audio.

    Steps:
        1. Convert images to animated clips (Ken Burns pan/zoom).
        2. Load each video clip.
        3. Trim to 3–8 seconds.
        4. Resize to target aspect.
        5. Apply cinematic effects (with configurable opacity/types).
        6. Concatenate (with optional glitch transitions at configurable opacity).
        7. Apply text overlays.
        8. Composite EQ visualizer overlay (if enabled).
        9. Apply beat flash (if enabled + audio analyzed).
        10. Attach audio track.
        11. Export H.264 / AAC.
    """
    target_w, target_h = PRESETS.get(aspect, PRESETS["vertical"])
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    all_sources = list(clip_paths or []) + list(image_paths or [])
    if not all_sources:
        raise ValueError("No clip or image paths provided")

    log.info(
        "Rendering video: %d clips + %d images → %s (%s %dx%d)",
        len(clip_paths or []), len(image_paths or []),
        output_path.name, aspect, target_w, target_h,
    )

    # ── 1. Convert images to animated clips ─────────────────────────────
    image_clips: list = []
    for img_path in (image_paths or []):
        log.info("  Converting image → clip: %s", img_path.name)
        try:
            ic = _image_to_clip(img_path, target_w, target_h, fps=fps, effect_config=effect_config)
            image_clips.append(ic)
        except Exception as exc:
            log.warning("  Skipping image %s — %s", img_path.name, exc)

    # ── 2. Load & prepare video clips ───────────────────────────────────
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
        with_fx = apply_effects(resized, config=effect_config)
        video_clips.append(with_fx)

    # ── 3. Interleave images and video clips ────────────────────────────
    prepared = _interleave(image_clips, video_clips)

    if not prepared:
        raise RuntimeError("No clips could be loaded — cannot render video")

    # ── 4. Concatenate ──────────────────────────────────────────────────
    if use_glitch_transitions and len(prepared) > 1:
        glitch_opacity = effect_config.glitch_opacity if effect_config else 1.0
        final_video = _concat_with_glitch(prepared, opacity=glitch_opacity)
    else:
        final_video = concatenate_videoclips(prepared, method="compose")

    # ── 5. Text overlays ────────────────────────────────────────────────
    if text_overlays:
        final_video = _apply_text_overlays(final_video, text_overlays, target_w, target_h)

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

    final_video.write_videofile(
        str(output_path),
        fps=fps,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        threads=4,
        logger=None,
    )

    # Cleanup
    final_video.close()
    for c in prepared:
        try:
            c.close()
        except Exception:
            pass

    log.info("✓ Video rendered: %s (%.1f KB)", output_path.name, output_path.stat().st_size / 1024)
    return output_path


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
    clip = apply_effects(clip, config=effect_config)
    log.info("    Image clip: %s → %.1fs (%s)", image_path.name, duration, direction)
    return clip


# ── Text overlay ────────────────────────────────────────────────────────────

def _get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Try to load a good font, fall back to default."""
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
        font = _get_font(font_size)
        color = _hex_to_rgb(ov.color)

        # Measure text
        tmp_img = Image.new("RGBA", (1, 1))
        draw = ImageDraw.Draw(tmp_img)

        # Handle multi-line text
        lines = ov.text.split("\\n") if "\\n" in ov.text else [ov.text]
        line_bboxes = []
        total_h = 0
        max_w = 0
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            lw = bbox[2] - bbox[0]
            lh = bbox[3] - bbox[1]
            line_bboxes.append((lw, lh))
            total_h += lh + 8  # 8px line spacing
            max_w = max(max_w, lw)

        # Padding
        pad = 20
        overlay_w = max_w + pad * 2
        overlay_h = total_h + pad * 2

        # Draw text overlay image
        overlay_img = Image.new("RGBA", (overlay_w, overlay_h), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay_img)

        # Semi-transparent background bar
        overlay_draw.rectangle(
            [(0, 0), (overlay_w, overlay_h)],
            fill=(0, 0, 0, 140),
        )

        y_cursor = pad
        for i, line in enumerate(lines):
            lw, lh = line_bboxes[i]
            x = (overlay_w - lw) // 2

            # Shadow
            if ov.shadow:
                overlay_draw.text((x + 2, y_cursor + 2), line, font=font, fill=(0, 0, 0, 200))

            overlay_draw.text((x, y_cursor), line, font=font, fill=(*color, 255))
            y_cursor += lh + 8

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


def _apply_visualizer(clip: VideoClip, viz_config: dict, fps: int) -> VideoClip:
    """Composite the EQ visualizer onto every frame of the clip."""
    from app.services.media.visualizer import render_visualizer_frame

    def _viz_frame(get_frame, t):
        frame = get_frame(t)
        frame_idx = int(t * fps)
        return render_visualizer_frame(frame, frame_idx, viz_config)

    return clip.transform(_viz_frame)
