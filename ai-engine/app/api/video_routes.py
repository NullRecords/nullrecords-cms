"""Video generation API routes.

POST /video/upload-audio — Upload an audio file via multipart form
GET  /video/audio-info   — Get duration/metadata of an uploaded audio file
POST /video/generate     — Generate a single video
POST /video/generate-batch — Auto-split audio into shorts + optional full-length
GET  /video/exports      — List exported videos
GET  /video/download/{filename} — Download an exported video file
POST /video/publish      — Publish to YouTube (auto) or get manual instructions for TikTok/IG
GET  /video/youtube/auth — Start YouTube OAuth2 flow
GET  /video/youtube/callback — OAuth2 callback
GET  /video/youtube/status — Check if YouTube is authenticated
"""

import logging
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.services.media.audio import get_duration_ms
from app.services.media.video_engine import VideoConfig, VideoEngine

log = logging.getLogger(__name__)
router = APIRouter(prefix="/video", tags=["video"])

_engine: VideoEngine | None = None

ALLOWED_AUDIO_EXT = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".wma"}
ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def _get_engine() -> VideoEngine:
    global _engine
    if _engine is None:
        _engine = VideoEngine()
    return _engine


def _uploads_dir() -> Path:
    """Return (and create) the audio uploads directory."""
    d = Path(get_settings().exports_dir) / "audio_uploads"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _image_uploads_dir() -> Path:
    """Return (and create) the image uploads directory."""
    d = Path(get_settings().exports_dir) / "image_uploads"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ── Schemas ─────────────────────────────────────────────────────────────────

class AudioInfoResponse(BaseModel):
    filename: str
    path: str
    duration_ms: int
    size_kb: float


class VideoGenerateRequest(BaseModel):
    audio_path: str = Field(..., description="Absolute or relative path to the audio file")
    start_ms: int = Field(0, ge=0)
    duration_ms: int = Field(15000, ge=1000, le=600000)
    mood: str = Field("")
    tags: list[str] = Field(default_factory=list)
    output_name: str = Field("")
    clip_count: int | None = Field(None, ge=2, le=20)
    fps: int = Field(24, ge=12, le=60)
    use_glitch_transitions: bool = Field(True)
    aspect: str = Field("vertical", description="'vertical' (9:16) or 'widescreen' (16:9)")

    # Image sourcing
    image_query: str = Field("", description="Pexels search term for background images (e.g. 'cyberpunk city')")
    image_urls: list[str] = Field(default_factory=list, description="Direct image URLs to use as backgrounds")
    image_paths: list[str] = Field(default_factory=list, description="Local image file paths")

    # Text overlays
    overlay_text: str = Field("", description="Main text overlay (track name, title)")
    overlay_subtitle: str = Field("", description="Subtitle overlay (artist, link)")
    overlay_position: str = Field("center", description="Text position: center, top, bottom, lower-third")

    # Effect configuration
    effect_opacity: float = Field(1.0, ge=0.0, le=1.0, description="Global effect layer opacity (0=transparent, 1=opaque)")
    glitch_opacity: float = Field(0.7, ge=0.0, le=1.0, description="Glitch transition opacity")
    color_shift_enabled: bool = Field(False, description="Enable chromatic aberration effect")
    scanline_enabled: bool = Field(False, description="Enable CRT scanline overlay")
    vhs_enabled: bool = Field(False, description="Enable VHS distortion effect")
    beat_flash_enabled: bool = Field(False, description="Flash on beat hits")

    # Visualizer configuration
    visualizer_enabled: bool = Field(False, description="Enable audio EQ visualizer overlay")
    visualizer_type: str = Field("bars", description="Visualizer type: bars, lines, waveform, circular")
    visualizer_color: str = Field("#00ffff", description="Primary visualizer color (hex)")
    visualizer_color2: str = Field("#ff5758", description="Secondary/gradient visualizer color (hex)")
    visualizer_opacity: float = Field(0.8, ge=0.0, le=1.0, description="Visualizer layer opacity")
    visualizer_intensity: float = Field(1.0, ge=0.1, le=3.0, description="Visualizer height/size multiplier")
    visualizer_position: str = Field("bottom", description="Visualizer position: bottom, center, top, full")
    visualizer_bar_count: int = Field(32, ge=8, le=128, description="Number of bars/lines in the visualizer")
    visualizer_glow: bool = Field(True, description="Enable glow effect on visualizer")
    show_song_info: bool = Field(True, description="Show song name and artist on visualizer")

    # Font / style configuration
    font_family: str = Field("", description="Font family for overlays (empty = AI-selected)")
    title_color: str = Field("", description="Title text color hex (empty = AI-selected)")
    subtitle_color: str = Field("", description="Subtitle text color hex (empty = AI-selected)")
    font_size_title: int = Field(0, ge=0, le=200, description="Title font size (0 = auto)")
    font_size_subtitle: int = Field(0, ge=0, le=200, description="Subtitle font size (0 = auto)")
    text_spacing: int = Field(0, ge=0, le=100, description="Line spacing in pixels (0 = auto)")


class VideoGenerateResponse(BaseModel):
    video_path: str
    filename: str
    size_kb: float
    duration_ms: int


class BatchGenerateRequest(BaseModel):
    audio_path: str = Field(..., description="Path to the audio file")
    segment_duration_ms: int = Field(15000, ge=5000, le=60000, description="Duration per short")
    mood: str = Field("")
    tags: list[str] = Field(default_factory=list)
    clip_count: int | None = Field(None, ge=2, le=20)
    fps: int = Field(24, ge=12, le=60)
    use_glitch_transitions: bool = Field(True)
    include_full_length: bool = Field(False, description="Also render one widescreen full-length video")


class BatchGenerateResponse(BaseModel):
    shorts: list[VideoGenerateResponse]
    full_length: VideoGenerateResponse | None = None


class VideoExport(BaseModel):
    filename: str
    path: str
    size_kb: float
    size_mb: float = 0
    modified_at: str = ""


class PublishRequest(BaseModel):
    video_path: str = Field(..., description="Path to the video file to publish")
    platforms: list[str] = Field(..., description="List of platforms: tiktok, instagram, youtube")
    title: str = Field("", description="Video title / caption")
    description: str = Field("", description="Video description")
    tags: list[str] = Field(default_factory=list, description="Hashtags / tags")
    youtube_privacy: str = Field("public", description="YouTube privacy: public, unlisted, private")


class PublishResult(BaseModel):
    platform: str
    status: str  # "uploaded", "manual", "error", "not_authenticated"
    message: str
    url: str | None = None
    download_url: str | None = None
    caption: str | None = None
    instructions: str | None = None


class PublishResponse(BaseModel):
    results: list[PublishResult]


# ── Routes ──────────────────────────────────────────────────────────────────

@router.post("/upload-audio", response_model=AudioInfoResponse)
async def upload_audio(file: UploadFile = File(...)):
    """Upload an audio file and return its path + duration."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_AUDIO_EXT:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format '{ext}'. Allowed: {', '.join(sorted(ALLOWED_AUDIO_EXT))}",
        )

    safe_name = f"{uuid.uuid4().hex[:8]}_{Path(file.filename).stem}{ext}"
    dest = _uploads_dir() / safe_name

    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    duration = get_duration_ms(dest)
    size_kb = round(dest.stat().st_size / 1024, 1)

    log.info("Audio uploaded: %s (%d ms, %.1f KB)", safe_name, duration, size_kb)
    return AudioInfoResponse(filename=safe_name, path=str(dest), duration_ms=duration, size_kb=size_kb)


@router.get("/audio-info", response_model=AudioInfoResponse)
def audio_info(path: str):
    """Get duration + size of an audio file already on disk."""
    p = Path(path)
    if not p.is_absolute():
        p = Path(get_settings().exports_dir).parent / p
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")

    return AudioInfoResponse(
        filename=p.name,
        path=str(p),
        duration_ms=get_duration_ms(p),
        size_kb=round(p.stat().st_size / 1024, 1),
    )


@router.post("/generate", response_model=VideoGenerateResponse)
def generate_video(req: VideoGenerateRequest, db: Session = Depends(get_db)):
    """Generate a single video from media assets + audio."""
    audio = _resolve_audio(req.audio_path)

    config = VideoConfig(
        audio_path=str(audio),
        start_ms=req.start_ms,
        duration_ms=req.duration_ms,
        mood=req.mood,
        tags=req.tags,
        output_name=req.output_name,
        clip_count=req.clip_count,
        fps=req.fps,
        use_glitch_transitions=req.use_glitch_transitions,
        aspect=req.aspect,
        image_query=req.image_query,
        image_urls=req.image_urls,
        image_paths=req.image_paths,
        overlay_text=req.overlay_text,
        overlay_subtitle=req.overlay_subtitle,
        overlay_position=req.overlay_position,
        # Effect config
        effect_opacity=req.effect_opacity,
        glitch_opacity=req.glitch_opacity,
        color_shift_enabled=req.color_shift_enabled,
        scanline_enabled=req.scanline_enabled,
        vhs_enabled=req.vhs_enabled,
        beat_flash_enabled=req.beat_flash_enabled,
        # Visualizer config
        visualizer_enabled=req.visualizer_enabled,
        visualizer_type=req.visualizer_type,
        visualizer_color=req.visualizer_color,
        visualizer_color2=req.visualizer_color2,
        visualizer_opacity=req.visualizer_opacity,
        visualizer_intensity=req.visualizer_intensity,
        visualizer_position=req.visualizer_position,
        visualizer_bar_count=req.visualizer_bar_count,
        visualizer_glow=req.visualizer_glow,
        show_song_info=req.show_song_info,
        # Font config
        font_family=req.font_family,
        title_color=req.title_color,
        subtitle_color=req.subtitle_color,
        font_size_title=req.font_size_title,
        font_size_subtitle=req.font_size_subtitle,
        text_spacing=req.text_spacing,
    )

    return _run_generate(db, config, req.duration_ms)


@router.post("/generate-batch", response_model=BatchGenerateResponse)
def generate_batch(req: BatchGenerateRequest, db: Session = Depends(get_db)):
    """Auto-split audio into multiple shorts, optionally plus one full-length widescreen video."""
    audio = _resolve_audio(req.audio_path)
    duration = get_duration_ms(audio)

    seg = req.segment_duration_ms
    shorts: list[VideoGenerateResponse] = []

    # Generate shorts segments
    offset = 0
    idx = 1
    while offset < duration:
        chunk = min(seg, duration - offset)
        if chunk < 3000:
            break  # skip very short tail

        config = VideoConfig(
            audio_path=str(audio),
            start_ms=offset,
            duration_ms=chunk,
            mood=req.mood,
            tags=req.tags,
            output_name=f"short_{idx:02d}",
            clip_count=req.clip_count,
            fps=req.fps,
            use_glitch_transitions=req.use_glitch_transitions,
            aspect="vertical",
        )
        shorts.append(_run_generate(db, config, chunk))
        offset += seg
        idx += 1

    # Optional full-length widescreen
    full: VideoGenerateResponse | None = None
    if req.include_full_length:
        full_config = VideoConfig(
            audio_path=str(audio),
            start_ms=0,
            duration_ms=duration,
            mood=req.mood,
            tags=req.tags,
            output_name="full_length",
            clip_count=max((req.clip_count or 4), duration // 5000),
            fps=req.fps,
            use_glitch_transitions=req.use_glitch_transitions,
            aspect="widescreen",
        )
        full = _run_generate(db, full_config, duration)

    return BatchGenerateResponse(shorts=shorts, full_length=full)


@router.get("/exports", response_model=list[VideoExport])
def list_exports():
    """List all previously generated videos (newest first)."""
    import datetime
    engine = _get_engine()
    raw = engine.list_exports()
    enriched = []
    for v in raw:
        p = Path(v.path) if isinstance(v, VideoExport) else Path(v["path"])
        fname = v.filename if isinstance(v, VideoExport) else v["filename"]
        sk = v.size_kb if isinstance(v, VideoExport) else v["size_kb"]
        mtime = ""
        if p.exists():
            ts = p.stat().st_mtime
            mtime = datetime.datetime.fromtimestamp(ts).isoformat(timespec="seconds")
        enriched.append(VideoExport(
            filename=fname, path=str(p),
            size_kb=sk, size_mb=round(sk / 1024, 1),
            modified_at=mtime,
        ))
    enriched.sort(key=lambda x: x.modified_at, reverse=True)
    return enriched


@router.get("/download/{filename}")
def download_export(filename: str):
    """Download an exported video file."""
    exports_dir = Path(get_settings().exports_dir) / "videos"
    # Sanitize — only allow simple filenames, no path traversal
    safe = Path(filename).name
    filepath = exports_dir / safe
    if not filepath.exists() or not filepath.is_file():
        raise HTTPException(status_code=404, detail=f"Video not found: {filename}")
    return FileResponse(
        path=str(filepath),
        media_type="video/mp4",
        filename=safe,
    )


@router.delete("/delete/{filename}")
def delete_export(filename: str):
    """Permanently delete an exported video file."""
    exports_dir = Path(get_settings().exports_dir) / "videos"
    safe = Path(filename).name
    filepath = exports_dir / safe
    if not filepath.exists() or not filepath.is_file():
        raise HTTPException(status_code=404, detail=f"Video not found: {filename}")
    filepath.unlink()
    log.info("Deleted video: %s", safe)
    return {"status": "deleted", "filename": safe}


@router.post("/archive/{filename}")
def archive_export(filename: str):
    """Move an exported video to the archive directory."""
    exports_dir = Path(get_settings().exports_dir) / "videos"
    safe = Path(filename).name
    filepath = exports_dir / safe
    if not filepath.exists() or not filepath.is_file():
        raise HTTPException(status_code=404, detail=f"Video not found: {filename}")

    archive_dir = exports_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    dest = archive_dir / safe
    shutil.move(str(filepath), str(dest))
    log.info("Archived video: %s → %s", safe, dest)
    return {"status": "archived", "filename": safe, "archive_path": str(dest)}


# ── Audio analysis ──────────────────────────────────────────────────────────

class AudioAnalysisResponse(BaseModel):
    beats: list[float] = Field(description="Beat timestamps in seconds")
    bpm: float
    levels: list[float] = Field(description="Per-frame RMS levels (0-1)")
    spectrum: list[list[float]] = Field(description="Per-frame spectrum bands")
    duration: float
    sample_rate: int
    fps: int
    n_frames: int


@router.post("/analyze-audio", response_model=AudioAnalysisResponse)
def analyze_audio(
    audio_path: str = Query(..., description="Path to audio file"),
    fps: int = Query(24, ge=12, le=60),
):
    """Analyze audio for beats, spectrum, and levels — used for visualizer config."""
    from app.services.media.audio_analyzer import analyze_audio as _analyze

    path = _resolve_audio(audio_path)
    try:
        result = _analyze(str(path), fps=fps)
    except Exception as e:
        log.exception("Audio analysis failed")
        raise HTTPException(status_code=422, detail=f"Audio analysis failed: {e}")

    return AudioAnalysisResponse(**result)


# ── Image management ────────────────────────────────────────────────────────

class ImageSearchRequest(BaseModel):
    query: str = Field(..., description="Search term for Pexels image search")
    count: int = Field(6, ge=1, le=20)


class ImageResult(BaseModel):
    source_id: str
    title: str
    url: str
    preview_url: str
    width: int = 0
    height: int = 0


class ImageUploadResponse(BaseModel):
    filename: str
    path: str
    size_kb: float


@router.post("/search-images", response_model=list[ImageResult])
def search_images(req: ImageSearchRequest):
    """Search Pexels for stock images to use as video backgrounds."""
    from app.services.media.image_source import search_pexels_images

    results = search_pexels_images(req.query, count=req.count)
    return [ImageResult(**r) for r in results]


@router.post("/upload-image", response_model=ImageUploadResponse)
async def upload_image(file: UploadFile = File(...)):
    """Upload an image file to use as a video background."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXT:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image format '{ext}'. Allowed: {', '.join(sorted(ALLOWED_IMAGE_EXT))}",
        )

    safe_name = f"{uuid.uuid4().hex[:8]}_{Path(file.filename).stem}{ext}"
    dest = _image_uploads_dir() / safe_name

    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    size_kb = round(dest.stat().st_size / 1024, 1)
    log.info("Image uploaded: %s (%.1f KB)", safe_name, size_kb)
    return ImageUploadResponse(filename=safe_name, path=str(dest), size_kb=size_kb)


@router.get("/images")
def list_images():
    """List all available images (uploaded + downloaded from Pexels)."""
    images = []
    # Check image uploads
    uploads = _image_uploads_dir()
    for f in uploads.glob("*"):
        if f.suffix.lower() in ALLOWED_IMAGE_EXT:
            images.append({
                "filename": f.name,
                "path": str(f),
                "size_kb": round(f.stat().st_size / 1024, 1),
                "source": "upload",
                "preview_url": f"/video/image-preview/{f.name}",
            })
    # Check media-library/images
    lib_images = Path(get_settings().media_library_dir) / "images"
    if lib_images.exists():
        for f in lib_images.glob("*"):
            if f.suffix.lower() in ALLOWED_IMAGE_EXT:
                images.append({
                    "filename": f.name,
                    "path": str(f),
                    "size_kb": round(f.stat().st_size / 1024, 1),
                    "source": "pexels",
                    "preview_url": f"/video/image-preview/{f.name}",
                })
    return images


@router.get("/image-preview/{filename}")
def image_preview(filename: str):
    """Serve an image for preview in the UI."""
    safe = Path(filename).name

    # Check uploads first
    p = _image_uploads_dir() / safe
    if p.exists() and p.is_file():
        media_type = "image/jpeg"
        if safe.endswith(".png"):
            media_type = "image/png"
        elif safe.endswith(".webp"):
            media_type = "image/webp"
        return FileResponse(path=str(p), media_type=media_type)

    # Check media-library/images
    lib = Path(get_settings().media_library_dir) / "images" / safe
    if lib.exists() and lib.is_file():
        media_type = "image/jpeg"
        if safe.endswith(".png"):
            media_type = "image/png"
        elif safe.endswith(".webp"):
            media_type = "image/webp"
        return FileResponse(path=str(lib), media_type=media_type)

    raise HTTPException(status_code=404, detail=f"Image not found: {filename}")


# ── YouTube OAuth2 ──────────────────────────────────────────────────────────

@router.get("/youtube/status")
def youtube_status():
    """Check whether YouTube OAuth is set up and authenticated."""
    from app.services.social.youtube import is_authenticated
    settings = get_settings()
    configured = bool(settings.youtube_client_id and settings.youtube_client_secret)
    return {
        "configured": configured,
        "authenticated": is_authenticated() if configured else False,
    }


@router.get("/youtube/auth")
def youtube_auth(redirect_uri: str = Query("http://localhost:8200/video/youtube/callback")):
    """Return the Google OAuth2 consent URL for YouTube upload permissions."""
    from app.services.social.youtube import get_auth_url
    try:
        url = get_auth_url(redirect_uri)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"auth_url": url}


@router.get("/youtube/callback")
def youtube_callback(
    code: str = Query(...),
    redirect_uri: str = Query("http://localhost:8200/video/youtube/callback"),
):
    """Handle the OAuth2 callback — exchange the code for tokens."""
    from app.services.social.youtube import exchange_code
    try:
        tokens = exchange_code(code, redirect_uri)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {e}")
    return {"status": "authenticated", "message": "YouTube tokens saved. You can now upload videos."}


# ── Publish ─────────────────────────────────────────────────────────────────

@router.post("/publish", response_model=PublishResponse)
def publish_video(req: PublishRequest):
    """Publish a video.

    - **youtube**: Auto-uploads if OAuth is authenticated.
    - **tiktok / instagram**: Returns download link + copy-ready caption + posting instructions.
    """
    from app.services.social.youtube import is_authenticated as yt_authed, upload_video as yt_upload
    from app.services.social.captions import (
        build_youtube_description,
        build_tiktok_caption,
        build_instagram_caption,
        TIKTOK_INSTRUCTIONS,
        INSTAGRAM_INSTRUCTIONS,
    )

    video = Path(req.video_path)
    if not video.exists():
        raise HTTPException(status_code=404, detail=f"Video not found: {req.video_path}")

    download_url = f"/video/download/{video.name}"
    results: list[PublishResult] = []

    for platform in req.platforms:
        p = platform.lower().strip()

        if p == "youtube":
            if not yt_authed():
                results.append(PublishResult(
                    platform="youtube",
                    status="not_authenticated",
                    message="YouTube not authenticated. Click 'Connect YouTube' to set up OAuth first.",
                ))
            else:
                try:
                    yt_desc = build_youtube_description(req.title, req.description, req.tags)
                    result = yt_upload(
                        video_path=str(video),
                        title=req.title or video.stem,
                        description=yt_desc,
                        tags=req.tags,
                        privacy=req.youtube_privacy,
                    )
                    results.append(PublishResult(
                        platform="youtube",
                        status="uploaded",
                        message=f"Uploaded to YouTube as '{req.title or video.stem}'",
                        url=result.get("url"),
                    ))
                except Exception as e:
                    log.exception("YouTube upload failed")
                    results.append(PublishResult(
                        platform="youtube",
                        status="error",
                        message=f"Upload failed: {e}",
                    ))

        elif p == "tiktok":
            caption = build_tiktok_caption(req.title, req.description, req.tags)
            results.append(PublishResult(
                platform="tiktok",
                status="manual",
                message="Download the video and post manually on TikTok.",
                download_url=download_url,
                caption=caption,
                instructions=TIKTOK_INSTRUCTIONS,
            ))

        elif p == "instagram":
            caption = build_instagram_caption(req.title, req.description, req.tags)
            results.append(PublishResult(
                platform="instagram",
                status="manual",
                message="Download the video and post as an Instagram Reel.",
                download_url=download_url,
                caption=caption,
                instructions=INSTAGRAM_INSTRUCTIONS,
            ))

        else:
            results.append(PublishResult(
                platform=p,
                status="error",
                message=f"Platform '{p}' is not supported. Use: youtube, tiktok, instagram.",
            ))

    return PublishResponse(results=results)


# ── Helpers ─────────────────────────────────────────────────────────────────

def _resolve_audio(audio_path: str) -> Path:
    """Resolve an audio path (absolute or relative to ai-engine root)."""
    audio = Path(audio_path)
    if not audio.is_absolute():
        audio = Path(get_settings().exports_dir).parent / audio
    if not audio.exists():
        raise HTTPException(status_code=404, detail=f"Audio file not found: {audio_path}")
    return audio


def _run_generate(db: Session, config: VideoConfig, duration_ms: int) -> VideoGenerateResponse:
    """Run the video engine and return a response model."""
    engine = _get_engine()
    try:
        result = engine.generate_video(db, config)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    stat = result.stat()
    return VideoGenerateResponse(
        video_path=str(result),
        filename=result.name,
        size_kb=round(stat.st_size / 1024, 1),
        duration_ms=duration_ms,
    )
