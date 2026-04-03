"""DJ & radio station discovery — local, national, and international.

Scrapes public web sources (DuckDuckGo, radio directories, DJ databases)
to find DJs, radio stations, and music shows that play nu jazz, experimental
electronic, and related genres. Targets are added as influencers for outreach.
"""

import html as html_mod
import logging
import re
import time
from typing import Any
from urllib.parse import quote_plus, unquote

import requests

logger = logging.getLogger(__name__)

_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
_HEADERS = {"User-Agent": _UA, "Accept-Language": "en-US,en;q=0.9"}
_TIMEOUT = 15


def _get(url: str, **kwargs) -> requests.Response | None:
    try:
        r = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT, **kwargs)
        r.raise_for_status()
        return r
    except Exception as exc:
        logger.debug("GET %s failed: %s", url, exc)
        return None


def _clean(text: str) -> str:
    text = html_mod.unescape(text)
    return re.sub(r"<[^>]+>", "", text).strip()


# ── DuckDuckGo discovery by category ────────────────────────────────────

# Organized by geographic scope and genre relevance
SEARCH_SETS = {
    # Jazz / experimental radio stations
    "jazz_radio": [
        "jazz radio station submit music",
        "nu jazz radio station playlist submission",
        "experimental jazz radio program",
        "jazz radio show independent music submission",
        "college radio jazz electronic",
        "community radio jazz experimental",
        "internet radio jazz electronic",
    ],
    # International stations
    "international_radio": [
        "radio station electronic jazz UK submit",
        "radio station jazz Germany submit music",
        "radio station jazz France submit",
        "radio station jazz Japan electronic",
        "radio station experimental music Australia",
        "world jazz radio station submission",
        "European jazz radio independent music",
        "BBC Radio 3 jazz submit",
        "NTS Radio submit music",
        "Worldwide FM submit",
        "FIP Radio jazz submit",
    ],
    # DJs - all levels
    "djs_jazz": [
        "DJ nu jazz experimental set",
        "jazz DJ Mixcloud playlist",
        "experimental electronic DJ booking",
        "nu jazz DJ radio mix",
        "acid jazz DJ contact",
    ],
    "djs_electronic": [
        "electronic music DJ jazz fusion",
        "downtempo DJ experimental playlist",
        "ambient jazz DJ set submit",
        "broken beat DJ contact booking",
        "future jazz DJ mix",
    ],
    "djs_international": [
        "DJ jazz London club night",
        "DJ nu jazz Berlin contact",
        "DJ jazz Tokyo experimental",
        "DJ jazz Paris electronic",
        "DJ Gilles Peterson contact",
        "DJ Lefto jazz contact",
        "DJ Toshio Matsuura contact",
    ],
    # Music blogs/press that cover jazz + electronic
    "jazz_press": [
        "jazz music blog submission independent",
        "experimental music review submission",
        "nu jazz album review blog",
        "jazz magazine submit music review",
        "electronic jazz music press contact",
    ],
    # Mixcloud / streaming DJs
    "mixcloud_djs": [
        "site:mixcloud.com nu jazz mix",
        "site:mixcloud.com experimental jazz",
        "site:mixcloud.com acid jazz",
        "site:mixcloud.com broken beat jazz",
    ],
}


def _search_ddg(query: str, max_results: int = 8) -> list[dict[str, Any]]:
    """Search DuckDuckGo HTML for results (no API key)."""
    results = []
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    resp = _get(url)
    if not resp:
        return results

    for m in re.finditer(
        r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.+?)</a>.*?'
        r'class="result__snippet"[^>]*>(.+?)</span>',
        resp.text, re.DOTALL,
    ):
        raw_link, title, snippet = m.group(1), _clean(m.group(2)), _clean(m.group(3))
        link = raw_link
        uddg = re.search(r'[?&]uddg=([^&]+)', raw_link)
        if uddg:
            link = unquote(uddg.group(1))

        results.append({
            "title": title[:200],
            "url": link,
            "snippet": snippet[:300],
        })
        if len(results) >= max_results:
            break

    return results


def _extract_domain(url: str) -> str:
    m = re.search(r'https?://(?:www\.)?([^/]+)', url)
    return m.group(1) if m else ""


def _classify_result(title: str, snippet: str, url: str, category: str) -> dict[str, Any]:
    """Classify a search result into a DJ or radio station influencer."""
    text_lower = f"{title} {snippet}".lower()
    domain = _extract_domain(url)

    # Determine platform
    platform = "web"
    if "mixcloud.com" in domain:
        platform = "mixcloud"
    elif "soundcloud.com" in domain:
        platform = "soundcloud"
    elif "youtube.com" in domain:
        platform = "youtube"
    elif "reddit.com" in domain:
        platform = "reddit"
    elif "instagram.com" in domain:
        platform = "instagram"

    # Determine type (DJ vs radio station vs show vs blog)
    target_type = "influencer"
    niche_prefix = ""
    if any(w in text_lower for w in ["radio station", "radio program", "fm ", "am ", "broadcasting"]):
        niche_prefix = "Radio: "
    elif any(w in text_lower for w in [" dj ", "disc jockey", "mixcloud", "mix set", "dj set"]):
        niche_prefix = "DJ: "
    elif any(w in text_lower for w in ["show", "program", "broadcast", "episode"]):
        niche_prefix = "Show: "
    elif any(w in text_lower for w in ["blog", "magazine", "review", "press"]):
        niche_prefix = "Press: "

    # Determine geographic scope
    scope = "national"
    if any(w in text_lower for w in ["local", "community", "college"]):
        scope = "local"
    elif any(w in text_lower for w in [
        "uk", "london", "bbc", "europe", "germany", "berlin", "france", "paris",
        "japan", "tokyo", "australia", "worldwide", "international", "global",
        "nts", "fip",
    ]):
        scope = "international"

    # Build niche description
    genre_tags = []
    for g in ["jazz", "nu jazz", "acid jazz", "experimental", "electronic",
              "downtempo", "broken beat", "ambient", "fusion", "future jazz"]:
        if g in text_lower:
            genre_tags.append(g)

    niche = f"{niche_prefix}{', '.join(genre_tags[:3]) if genre_tags else category} ({scope})"

    return {
        "handle": title[:80],
        "platform": platform,
        "followers": 0,
        "niche": niche[:120],
        "contact": url,
        "scope": scope,
        "category": category,
    }


# ── Main discovery functions ─────────────────────────────────────────────

def discover_dj_radio(categories: list[str] | None = None) -> list[dict[str, Any]]:
    """Discover DJs, radio stations, and shows across all categories.

    Args:
        categories: Subset of SEARCH_SETS keys to search. None = all.

    Returns:
        List of influencer dicts ready for DB insertion.
    """
    all_results: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    search_categories = categories or list(SEARCH_SETS.keys())

    for category in search_categories:
        queries = SEARCH_SETS.get(category, [])
        logger.info("DJ/Radio discovery: category=%s, queries=%d", category, len(queries))

        for query in queries:
            ddg_results = _search_ddg(query)
            time.sleep(2)  # Rate limit between DuckDuckGo requests
            for r in ddg_results:
                url = r["url"]
                if url in seen_urls:
                    continue
                # Skip irrelevant major platforms
                domain = _extract_domain(url)
                if any(s in domain for s in [
                    "amazon.", "ebay.", "wikipedia.", "facebook.com",
                    "twitter.com", "x.com", "tiktok.com", "spotify.com",
                ]):
                    continue
                seen_urls.add(url)
                classified = _classify_result(
                    r["title"], r["snippet"], url, category,
                )
                all_results.append(classified)

    logger.info(
        "DJ/Radio discovery complete: %d unique targets across %d categories",
        len(all_results), len(search_categories),
    )

    # Sort by scope priority: international first, then national, then local
    scope_order = {"international": 0, "national": 1, "local": 2}
    all_results.sort(key=lambda x: scope_order.get(x.get("scope", "national"), 1))

    return all_results


def discover_radio_stations() -> list[dict[str, Any]]:
    """Discover radio stations specifically."""
    return discover_dj_radio(categories=["jazz_radio", "international_radio"])


def discover_djs() -> list[dict[str, Any]]:
    """Discover DJs specifically."""
    return discover_dj_radio(categories=["djs_jazz", "djs_electronic", "djs_international", "mixcloud_djs"])


def discover_press() -> list[dict[str, Any]]:
    """Discover music press/blogs specifically."""
    return discover_dj_radio(categories=["jazz_press"])
