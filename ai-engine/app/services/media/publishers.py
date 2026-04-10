"""Video publishing service for YouTube, TikTok, and Instagram.

Provides a unified interface for posting videos to multiple platforms:
- YouTube: Fully automated via OAuth2
- TikTok/Instagram: Manual posting with generated captions

For TikTok/Instagram automation without API access, see the browser_publisher
module which uses Playwright for browser automation.
"""

import logging
from pathlib import Path

log = logging.getLogger(__name__)


def publish_video(
    video_path: str,
    title: str,
    description: str,
    tags: list[str],
    platforms: list[str],
    youtube_privacy: str = "public",
) -> list[dict]:
    """Publish a video to one or more platforms.

    Args:
        video_path: Path to the video file
        title: Video title / caption
        description: Video description
        tags: List of hashtags/tags
        platforms: List of platforms: youtube, tiktok, instagram
        youtube_privacy: YouTube privacy setting: public, unlisted, private

    Returns:
        List of result dicts with keys: platform, status, message, url, video_id, error
    """
    from app.services.social.youtube import is_authenticated as yt_authed, upload_video as yt_upload
    from app.services.social.captions import (
        build_youtube_description,
        build_tiktok_caption,
        build_instagram_caption,
    )

    video = Path(video_path)
    if not video.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    results = []

    for platform in platforms:
        p = platform.lower().strip()

        if p == "youtube":
            if not yt_authed():
                results.append({
                    "platform": "youtube",
                    "status": "not_authenticated",
                    "message": "YouTube OAuth not configured. Run /video/youtube/auth to connect.",
                })
            else:
                try:
                    yt_desc = build_youtube_description(title, description, tags)
                    result = yt_upload(
                        video_path=str(video),
                        title=title or video.stem,
                        description=yt_desc,
                        tags=tags,
                        privacy=youtube_privacy,
                    )
                    results.append({
                        "platform": "youtube",
                        "status": "uploaded",
                        "message": f"Uploaded to YouTube: {result.get('url', '')}",
                        "url": result.get("url"),
                        "video_id": result.get("video_id"),
                    })
                    log.info("YouTube upload successful: %s", result.get("video_id"))
                except Exception as e:
                    log.exception("YouTube upload failed")
                    results.append({
                        "platform": "youtube",
                        "status": "error",
                        "message": str(e),
                        "error": str(e),
                    })

        elif p == "tiktok":
            caption = build_tiktok_caption(title, description, tags)
            # Try browser automation if available
            auto_result = _try_browser_post("tiktok", str(video), caption)
            if auto_result:
                results.append(auto_result)
            else:
                results.append({
                    "platform": "tiktok",
                    "status": "manual",
                    "message": "Video ready for manual posting to TikTok",
                    "caption": caption,
                })

        elif p == "instagram":
            caption = build_instagram_caption(title, description, tags)
            # Try browser automation if available
            auto_result = _try_browser_post("instagram", str(video), caption)
            if auto_result:
                results.append(auto_result)
            else:
                results.append({
                    "platform": "instagram",
                    "status": "manual",
                    "message": "Video ready for manual posting to Instagram Reels",
                    "caption": caption,
                })

        else:
            results.append({
                "platform": p,
                "status": "error",
                "message": f"Unsupported platform: {p}",
            })

    return results


def _try_browser_post(platform: str, video_path: str, caption: str) -> dict | None:
    """Attempt to post via browser automation (Playwright).

    Returns result dict if successful/attempted, None to fall back to manual.
    """
    try:
        from app.services.social.browser_publisher import post_to_platform, is_configured
        if is_configured(platform):
            return post_to_platform(platform, video_path, caption)
    except ImportError:
        pass  # Browser automation not installed
    except Exception as e:
        log.warning("Browser automation failed for %s: %s", platform, e)
    return None
