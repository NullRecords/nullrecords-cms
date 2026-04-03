"""Playlist & influencer discovery — no API keys required.

Scrapes publicly accessible sources across multiple platforms relevant to
independent / experimental music: Bandcamp, SoundCloud, YouTube, Reddit,
music blogs, and more.
"""

import html as html_mod
import logging
import re
from typing import Any
from urllib.parse import quote_plus, urljoin

import requests

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
_HEADERS = {"User-Agent": _UA, "Accept-Language": "en-US,en;q=0.9"}
_TIMEOUT = 15


# ── helpers ──────────────────────────────────────────────────────────────

def _get(url: str, **kwargs) -> requests.Response | None:
    """GET with shared headers & timeout; returns None on failure."""
    try:
        r = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT, **kwargs)
        r.raise_for_status()
        return r
    except Exception as exc:
        logger.debug("GET %s failed: %s", url, exc)
        return None


def _clean(text: str) -> str:
    """Strip HTML tags and unescape entities."""
    text = html_mod.unescape(text)
    return re.sub(r"<[^>]+>", "", text).strip()


# ── Bandcamp ─────────────────────────────────────────────────────────────

def _discover_bandcamp(query: str) -> tuple[list[dict], list[dict]]:
    """Search Bandcamp for labels, artists, and albums (public, no key)."""
    playlists: list[dict[str, Any]] = []
    influencers: list[dict[str, Any]] = []

    url = f"https://bandcamp.com/search?q={quote_plus(query)}&item_type=b"  # bands/artists
    resp = _get(url)
    if not resp:
        return playlists, influencers

    # Parse search result cards from HTML
    for m in re.finditer(
        r'class="heading">\s*<a href="(https?://[^"]+)"[^>]*>([^<]+)</a>.*?'
        r'class="subhead">\s*([^<]*)',
        resp.text, re.DOTALL,
    ):
        link, name, sub = m.group(1), _clean(m.group(2)), _clean(m.group(3))
        influencers.append({
            "handle": name,
            "platform": "bandcamp",
            "followers": 0,
            "niche": sub[:120] if sub else query,
            "contact": link,
        })
        if len(influencers) >= 10:
            break

    # Also search for albums/labels as "playlists"
    url2 = f"https://bandcamp.com/search?q={quote_plus(query)}&item_type=a"  # albums
    resp2 = _get(url2)
    if resp2:
        for m in re.finditer(
            r'class="heading">\s*<a href="(https?://[^"]+)"[^>]*>([^<]+)</a>.*?'
            r'class="subhead">\s*([^<]*?)(?:</div>|<span)',
            resp2.text, re.DOTALL,
        ):
            link, name, sub = m.group(1), _clean(m.group(2)), _clean(m.group(3))
            parts = [p.strip() for p in sub.split("by") if p.strip()]
            curator = parts[-1] if len(parts) > 1 else ""
            playlists.append({
                "name": name,
                "platform": "bandcamp",
                "curator_name": curator,
                "followers": 0,
                "contact": "",
                "url": link,
            })
            if len(playlists) >= 8:
                break

    logger.info("Bandcamp: found %d influencers, %d playlists", len(influencers), len(playlists))
    return playlists, influencers


# ── SoundCloud ───────────────────────────────────────────────────────────

def _discover_soundcloud(query: str) -> tuple[list[dict], list[dict]]:
    """Search SoundCloud for users and playlists (public HTML, no key)."""
    playlists: list[dict[str, Any]] = []
    influencers: list[dict[str, Any]] = []

    url = f"https://soundcloud.com/search/people?q={quote_plus(query)}"
    resp = _get(url)
    if not resp:
        return playlists, influencers

    # SoundCloud embeds hydration data in a script tag
    for m in re.finditer(
        r'"username"\s*:\s*"([^"]+)".*?"permalink"\s*:\s*"([^"]+)".*?'
        r'"followers_count"\s*:\s*(\d+).*?"description"\s*:\s*"([^"]*)"',
        resp.text, re.DOTALL,
    ):
        name, slug, followers, desc = m.group(1), m.group(2), int(m.group(3)), m.group(4)
        influencers.append({
            "handle": name,
            "platform": "soundcloud",
            "followers": followers,
            "niche": _clean(desc)[:120] if desc else query,
            "contact": f"https://soundcloud.com/{slug}",
        })
        if len(influencers) >= 10:
            break

    # Playlist search
    url2 = f"https://soundcloud.com/search/sets?q={quote_plus(query)}"
    resp2 = _get(url2)
    if resp2:
        for m in re.finditer(
            r'"title"\s*:\s*"([^"]+)".*?"permalink_url"\s*:\s*"(https://soundcloud\.com/[^"]+)".*?'
            r'"username"\s*:\s*"([^"]+)"',
            resp2.text, re.DOTALL,
        ):
            title, link, curator = m.group(1), m.group(2), m.group(3)
            playlists.append({
                "name": _clean(title),
                "platform": "soundcloud",
                "curator_name": _clean(curator),
                "followers": 0,
                "contact": "",
                "url": link,
            })
            if len(playlists) >= 8:
                break

    logger.info("SoundCloud: found %d influencers, %d playlists", len(influencers), len(playlists))
    return playlists, influencers


# ── YouTube (public search, no API key) ──────────────────────────────────

def _discover_youtube(query: str) -> tuple[list[dict], list[dict]]:
    """Search YouTube via public search results (no API key needed)."""
    playlists: list[dict[str, Any]] = []
    influencers: list[dict[str, Any]] = []

    search_query = f"{query} music channel"
    url = f"https://www.youtube.com/results?search_query={quote_plus(search_query)}&sp=EgIQAg%3D%3D"  # filter: channels
    resp = _get(url)
    if not resp:
        return playlists, influencers

    # YouTube embeds initial data in a script tag
    match = re.search(r'var ytInitialData = ({.*?});\s*</script>', resp.text, re.DOTALL)
    if not match:
        logger.debug("YouTube: no ytInitialData found")
        return playlists, influencers

    import json
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return playlists, influencers

    # Navigate the nested structure to find channel results
    try:
        sections = data["contents"]["twoColumnSearchResultsRenderer"]["primaryContents"]["sectionListRenderer"]["contents"]
        for section in sections:
            items = section.get("itemSectionRenderer", {}).get("contents", [])
            for item in items:
                ch = item.get("channelRenderer")
                if not ch:
                    continue
                title = ch.get("title", {}).get("simpleText", "")
                cid = ch.get("channelId", "")
                desc_runs = ch.get("descriptionSnippet", {}).get("runs", [])
                desc = "".join(r.get("text", "") for r in desc_runs)[:120]
                sub_text = ch.get("subscriberCountText", {}).get("simpleText", "0")
                # Parse "1.2M subscribers" → rough int
                followers = _parse_sub_count(sub_text)
                influencers.append({
                    "handle": title,
                    "platform": "youtube",
                    "followers": followers,
                    "niche": desc if desc else query,
                    "contact": f"https://www.youtube.com/channel/{cid}" if cid else "",
                })
                if len(influencers) >= 10:
                    break
    except (KeyError, TypeError):
        logger.debug("YouTube: failed to parse ytInitialData structure")

    logger.info("YouTube: found %d influencers", len(influencers))
    return playlists, influencers


def _parse_sub_count(text: str) -> int:
    """Parse '1.2M subscribers' or '45K subscribers' to an integer."""
    text = text.lower().replace(",", "").replace("subscribers", "").replace("subscriber", "").strip()
    m = re.match(r'([\d.]+)\s*([kmb]?)', text)
    if not m:
        return 0
    num = float(m.group(1))
    suffix = m.group(2)
    mult = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}.get(suffix, 1)
    return int(num * mult)


# ── Reddit ───────────────────────────────────────────────────────────────

def _discover_reddit(query: str) -> tuple[list[dict], list[dict]]:
    """Search Reddit for relevant subreddits and curators (public JSON API)."""
    playlists: list[dict[str, Any]] = []
    influencers: list[dict[str, Any]] = []

    # Search subreddits as "playlists" / communities
    url = f"https://www.reddit.com/subreddits/search.json?q={quote_plus(query + ' music')}&limit=10"
    resp = _get(url)
    if resp:
        try:
            children = resp.json().get("data", {}).get("children", [])
            for child in children:
                d = child.get("data", {})
                name = d.get("display_name_prefixed", "")
                desc = d.get("public_description", "")
                subs = d.get("subscribers", 0)
                playlists.append({
                    "name": name,
                    "platform": "reddit",
                    "curator_name": "",
                    "followers": subs,
                    "contact": "",
                    "url": f"https://www.reddit.com/{name}" if name else "",
                })
        except Exception:
            pass

    logger.info("Reddit: found %d communities", len(playlists))
    return playlists, influencers


# ── Music blogs (DuckDuckGo HTML search) ─────────────────────────────────

def _discover_blogs(query: str) -> tuple[list[dict], list[dict]]:
    """Find music blogs and curators via DuckDuckGo HTML search (no key)."""
    playlists: list[dict[str, Any]] = []
    influencers: list[dict[str, Any]] = []

    search_terms = f"{query} music blog curator playlist"
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(search_terms)}"
    resp = _get(url)
    if not resp:
        return playlists, influencers

    # Parse DuckDuckGo HTML results
    for m in re.finditer(
        r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.+?)</a>.*?'
        r'class="result__snippet"[^>]*>(.+?)</span>',
        resp.text, re.DOTALL,
    ):
        raw_link, title, snippet = m.group(1), _clean(m.group(2)), _clean(m.group(3))
        # Resolve DuckDuckGo redirect URLs
        link = raw_link
        uddg = re.search(r'[?&]uddg=([^&]+)', raw_link)
        if uddg:
            from urllib.parse import unquote
            link = unquote(uddg.group(1))
        # Skip major platforms — we handle those separately
        if any(s in link.lower() for s in ["youtube.com", "soundcloud.com", "bandcamp.com", "reddit.com", "spotify.com"]):
            continue
        influencers.append({
            "handle": title[:80],
            "platform": "blog",
            "followers": 0,
            "niche": snippet[:120],
            "contact": link,
        })
        if len(influencers) >= 8:
            break

    logger.info("Blogs: found %d curators/blogs", len(influencers))
    return playlists, influencers


# ── Public entry points (called by outreach_routes) ─────────────────────

def discover_playlists(query: str) -> list[dict[str, Any]]:
    """Discover playlists across all public platforms. No API keys needed."""
    all_playlists: list[dict[str, Any]] = []

    for source_fn in [_discover_bandcamp, _discover_soundcloud, _discover_youtube, _discover_reddit, _discover_blogs]:
        try:
            pl, _ = source_fn(query)
            all_playlists.extend(pl)
        except Exception as exc:
            logger.warning("Playlist discovery error in %s: %s", source_fn.__name__, exc)

    logger.info("Total playlists discovered: %d", len(all_playlists))
    return all_playlists


def discover_influencers(query: str) -> list[dict[str, Any]]:
    """Discover influencers/curators across all public platforms. No API keys needed."""
    all_influencers: list[dict[str, Any]] = []

    for source_fn in [_discover_bandcamp, _discover_soundcloud, _discover_youtube, _discover_reddit, _discover_blogs]:
        try:
            _, inf = source_fn(query)
            all_influencers.extend(inf)
        except Exception as exc:
            logger.warning("Influencer discovery error in %s: %s", source_fn.__name__, exc)

    logger.info("Total influencers discovered: %d", len(all_influencers))
    return all_influencers


# ── Legacy aliases (kept for backward compat if anything references them) ─

def discover_spotify_playlists(query: str) -> list[dict[str, Any]]:
    """Legacy wrapper — now uses multi-platform discovery."""
    return discover_playlists(query)


def discover_youtube_channels(query: str) -> list[dict[str, Any]]:
    """Legacy wrapper — now uses multi-platform discovery."""
    return discover_influencers(query)
