"""Video generation API routes.

POST /video/upload-audio — Upload an audio file via multipart form
GET  /video/audio-info   — Get duration/metadata of an uploaded audio file
POST /video/generate     — Generate a single video
POST /video/generate-batch — Auto-split audio into shorts + optional full-length
GET  /video/exports      — List exported videos
POST /video/publish      — Publish a video to TikTok/Instagram/YouTube
"""

import logging
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
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


class PublishRequest(BaseModel):
    video_path: str = Field(..., description="Path to the video file to publish")
    platforms: list[str] = Field(..., description="List of platforms: tiktok, instagram, youtube")
    title: str = Field("", description="Video title (YouTube)")
    description: str = Field("", description="Video description / caption")
    tags: list[str] = Field(default_factory=list, description="Hashtags / tags")


class PublishResult(BaseModel):
    platform: str
    status: str
    message: str
    url: str | None = None


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
    """List all previously generated videos."""
    engine = _get_engine()
    return engine.list_exports()


@router.post("/publish", response_model=PublishResponse)
def publish_video(req: PublishRequest):
    """Publish an exported video to social platforms.

    Currently returns setup instructions — actual OAuth upload requires
    configuring API credentials in .env for each platform.
    """
    video = Path(req.video_path)
    if not video.exists():
        raise HTTPException(status_code=404, detail=f"Video not found: {req.video_path}")

    results: list[PublishResult] = []
    settings = get_settings()

    for platform in req.platforms:
        p = platform.lower().strip()
        if p == "tiktok":
            key = getattr(settings, "tiktok_api_key", None) if hasattr(settings, "tiktok_api_key") else None
            if not key:
                results.append(PublishResult(
                    platform="tiktok",
                    status="not_configured",
                    message="Set TIKTOK_API_KEY and TIKTOK_API_SECRET in .env, then authenticate via TikTok Content Posting API.",
                ))
            else:
                results.append(PublishResult(
                    platform="tiktok", status="ready",
                    message="TikTok API configured. Upload will be implemented with the Content Posting API.",
                ))
        elif p == "instagram":
            key = getattr(settings, "instagram_access_token", None) if hasattr(settings, "instagram_access_token") else None
            if not key:
                results.append(PublishResult(
                    platform="instagram",
                    status="not_configured",
                    message="Set INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_BUSINESS_ID in .env via Facebook Graph API.",
                ))
            else:
                results.append(PublishResult(
                    platform="instagram", status="ready",
                    message="Instagram API configured. Upload via Reels Publishing API.",
                ))
        elif p == "youtube":
            key = getattr(settings, "youtube_api_key", None) if hasattr(settings, "youtube_api_key") else None
            if not key:
                results.append(PublishResult(
                    platform="youtube",
                    status="not_configured",
                    message="Set YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET in .env, then authenticate via YouTube Data API v3.",
                ))
            else:
                results.append(PublishResult(
                    platform="youtube", status="ready",
                    message="YouTube API configured. Upload via YouTube Data API v3.",
                ))
        else:
            results.append(PublishResult(
                platform=p, status="unsupported",
                message=f"Platform '{p}' is not supported. Use: tiktok, instagram, youtube.",
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
