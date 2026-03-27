"""Social caption helpers — generate platform-specific copy for manual posting."""


def build_youtube_description(title: str, description: str, tags: list[str]) -> str:
    """Full YouTube description with hashtags at the end."""
    parts = []
    if description:
        parts.append(description)
    parts.append("")
    parts.append("🎵 NullRecords — nu jazz, experimental electronic")
    parts.append("https://nullrecords.com")
    parts.append("")
    if tags:
        parts.append(" ".join(f"#{t.lstrip('#').replace(' ', '')}" for t in tags))
    return "\n".join(parts)


def build_tiktok_caption(title: str, description: str, tags: list[str]) -> str:
    """Short TikTok caption (150 char limit guideline) with hashtags."""
    hashtags = " ".join(f"#{t.lstrip('#').replace(' ', '')}" for t in tags) if tags else "#nullrecords #newmusic"
    caption = title or description or "New from NullRecords"
    # Keep it punchy
    if len(caption) > 100:
        caption = caption[:97] + "..."
    return f"{caption} {hashtags}"


def build_instagram_caption(title: str, description: str, tags: list[str]) -> str:
    """Instagram Reels caption with hashtags block."""
    parts = []
    if title:
        parts.append(title)
    if description:
        parts.append(description)
    if not parts:
        parts.append("New release from NullRecords 🎵")
    parts.append("")
    parts.append("🔗 Link in bio — nullrecords.com")
    parts.append("")
    default_tags = ["nullrecords", "newmusic", "nujazz", "experimentalelectronic", "musicvideo"]
    all_tags = [t.lstrip("#").replace(" ", "") for t in tags] if tags else []
    all_tags = list(dict.fromkeys(all_tags + default_tags))  # dedupe, preserve order
    parts.append(" ".join(f"#{t}" for t in all_tags[:30]))
    return "\n".join(parts)


TIKTOK_INSTRUCTIONS = """## How to post on TikTok

1. **Download** the video file using the button above
2. Open the **TikTok app** on your phone
3. Tap **+** (create) → **Upload** → select the video
4. **Paste the caption** (copied to your clipboard) into the description
5. Settings to check:
   - **Who can view**: Everyone
   - **Allow comments**: On
   - **Allow duets/stitches**: On (helps discovery)
6. Tap **Post**

### Tagging tips for TikTok
- Keep the caption short and punchy (under 150 chars before hashtags)
- Use 3-5 relevant hashtags — mix popular (#newmusic) with niche (#nujazz)
- First 2 seconds matter most — TikTok's algorithm decides reach quickly
"""

INSTAGRAM_INSTRUCTIONS = """## How to post on Instagram Reels

1. **Download** the video file using the button above
2. Open **Instagram** → tap **+** → **Reel**
3. Select the downloaded video from your camera roll
4. On the editing screen:
   - Add **music/audio** if desired (or keep original)
   - Trim if needed (Instagram Reels: 15s-90s performs best)
5. **Paste the caption** (copied to your clipboard)
6. Settings:
   - **Share to Feed**: On (increases reach)
   - **Tag people / location** if relevant
7. Tap **Share**

### Tagging tips for Instagram
- Up to 30 hashtags allowed — use a mix of sizes
- Put hashtags at the end of the caption or in first comment
- Tag @nullrecords and any featured artists
- Add relevant location tags for local discovery
"""
