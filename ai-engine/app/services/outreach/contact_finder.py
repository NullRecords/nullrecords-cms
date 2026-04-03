"""Contact email discovery for playlists and influencers.

Scrapes public web pages to find email addresses and social media contacts.
Supports: YouTube About pages, blog pages, Reddit sidebars, Bandcamp, SoundCloud.
"""

import logging
import re
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
_HEADERS = {"User-Agent": _UA, "Accept-Language": "en-US,en;q=0.9"}
_TIMEOUT = 15

# Pre-compiled email regex — matches common email patterns, filters out images/css
_EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)

# Domains to ignore (not real contact emails)
_IGNORE_DOMAINS = {
    "example.com", "sentry.io", "w3.org", "schema.org",
    "googleapis.com", "google.com", "gstatic.com",
    "facebook.com", "twitter.com", "instagram.com",
    "youtube.com", "youtu.be", "github.com",
    "apple.com", "microsoft.com", "mozilla.org",
    "jquery.com", "cloudflare.com", "cdn.com",
    "wixpress.com", "squarespace.com", "wordpress.com",
}

# File extensions that indicate non-email addresses
_IGNORE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".css", ".js", ".woff", ".ttf"}


def _get(url: str) -> Optional[requests.Response]:
    try:
        r = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT, allow_redirects=True)
        r.raise_for_status()
        return r
    except Exception as exc:
        logger.debug("GET %s failed: %s", url, exc)
        return None


def _extract_emails(text: str) -> list[str]:
    """Extract valid email addresses from text, filtering noise."""
    raw = _EMAIL_RE.findall(text)
    emails = []
    seen = set()
    for email in raw:
        email_lower = email.lower()
        if email_lower in seen:
            continue
        seen.add(email_lower)

        domain = email_lower.split("@")[1]
        if domain in _IGNORE_DOMAINS:
            continue
        if any(email_lower.endswith(ext) for ext in _IGNORE_EXTENSIONS):
            continue
        # Skip very long addresses (likely encoded data)
        if len(email) > 60:
            continue
        # Skip addresses that look like code variables
        if email.startswith("{{") or email.endswith("}}"):
            continue

        emails.append(email)
    return emails


def _extract_social_handles(text: str, soup: Optional[BeautifulSoup] = None) -> dict[str, str]:
    """Extract social media handles/links from page text and links."""
    socials = {}

    # Look for social links in anchor tags
    if soup:
        for a in soup.find_all("a", href=True):
            href = a["href"].lower()
            if "twitter.com/" in href or "x.com/" in href:
                handle = href.rstrip("/").split("/")[-1]
                if handle and handle not in ("intent", "share", "home"):
                    socials["twitter"] = f"@{handle}"
            elif "instagram.com/" in href:
                handle = href.rstrip("/").split("/")[-1]
                if handle and handle not in ("p", "explore", "accounts"):
                    socials["instagram"] = f"@{handle}"
            elif "tiktok.com/@" in href:
                handle = href.rstrip("/").split("@")[-1]
                if handle:
                    socials["tiktok"] = f"@{handle}"
            elif "facebook.com/" in href:
                handle = href.rstrip("/").split("/")[-1]
                if handle and handle not in ("sharer", "dialog", "share"):
                    socials["facebook"] = handle

    # Look for "DM" or "message" patterns in text
    dm_patterns = [
        r"(?:DM|message|contact)\s+(?:us\s+)?(?:on|at|via)\s+(?:Instagram|Twitter|TikTok)\s*[:\-]?\s*@?(\w+)",
        r"@(\w{3,20})\s+(?:on\s+)?(?:Instagram|Twitter|TikTok)",
    ]
    for pattern in dm_patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            socials.setdefault("dm_handle", m.group(1))

    return socials


def find_youtube_contact(channel_url: str) -> dict:
    """Scrape a YouTube channel's About page for email and social links.

    YouTube's about page typically shows a "View Email Address" button,
    but we can often find emails in the description or linked pages.
    """
    result = {"email": None, "socials": {}, "source": "youtube"}

    # Normalize URL to About page
    about_url = channel_url.rstrip("/")
    if "/about" not in about_url:
        about_url += "/about"

    resp = _get(about_url)
    if not resp:
        # Try the main page
        resp = _get(channel_url)
    if not resp:
        return result

    text = resp.text

    # YouTube embeds channel description and links in JSON within the page
    # Look for email in the page source
    emails = _extract_emails(text)
    if emails:
        result["email"] = emails[0]

    # Look for social links in the page
    soup = BeautifulSoup(text, "html.parser")
    result["socials"] = _extract_social_handles(text, soup)

    # YouTube has "links" section — look for them in JSON data
    link_patterns = re.findall(r'"url"\s*:\s*"(https?://[^"]+)"', text)
    for link in link_patterns:
        link_lower = link.lower()
        if "twitter.com/" in link_lower or "x.com/" in link_lower:
            handle = link.rstrip("/").split("/")[-1]
            if handle and len(handle) > 1:
                result["socials"]["twitter"] = f"@{handle}"
        elif "instagram.com/" in link_lower:
            handle = link.rstrip("/").split("/")[-1]
            if handle and len(handle) > 1:
                result["socials"]["instagram"] = f"@{handle}"

    logger.info("YouTube %s: email=%s, socials=%s", channel_url, result["email"], result["socials"])
    return result


def find_blog_contact(blog_url: str) -> dict:
    """Scrape a blog/website for contact information."""
    result = {"email": None, "socials": {}, "source": "blog"}

    # Try the main page first
    resp = _get(blog_url)
    if not resp:
        return result

    soup = BeautifulSoup(resp.text, "html.parser")
    page_text = soup.get_text(separator=" ")

    # Extract emails from visible text
    emails = _extract_emails(page_text)
    if emails:
        result["email"] = emails[0]

    result["socials"] = _extract_social_handles(page_text, soup)

    # If no email found on the main page, try common contact page paths
    if not result["email"]:
        base = blog_url.rstrip("/")
        for path in ["/contact", "/about", "/contact-us", "/submit", "/submissions"]:
            contact_resp = _get(base + path)
            if contact_resp:
                contact_soup = BeautifulSoup(contact_resp.text, "html.parser")
                contact_text = contact_soup.get_text(separator=" ")
                emails = _extract_emails(contact_text)
                if emails:
                    result["email"] = emails[0]
                    # Also grab socials from the contact page
                    more_socials = _extract_social_handles(contact_text, contact_soup)
                    result["socials"].update(more_socials)
                    break

    # Look for mailto: links
    if not result["email"]:
        for a in soup.find_all("a", href=True):
            if a["href"].startswith("mailto:"):
                email = a["href"].replace("mailto:", "").split("?")[0].strip()
                if _EMAIL_RE.match(email):
                    domain = email.lower().split("@")[1]
                    if domain not in _IGNORE_DOMAINS:
                        result["email"] = email
                        break

    logger.info("Blog %s: email=%s, socials=%s", blog_url, result["email"], result["socials"])
    return result


def find_reddit_contact(subreddit_url: str) -> dict:
    """Check a subreddit sidebar/wiki for contact info.

    Reddit doesn't typically have direct email contacts, so we look
    for linked Discord servers, social accounts, or email addresses
    in the sidebar.
    """
    result = {"email": None, "socials": {}, "source": "reddit"}

    # Use old.reddit.com for easier scraping of sidebar
    sub_name = subreddit_url.rstrip("/").split("/")[-1]
    if sub_name.startswith("r/"):
        sub_name = sub_name[2:]

    old_url = f"https://old.reddit.com/r/{sub_name}"
    resp = _get(old_url)
    if not resp:
        return result

    soup = BeautifulSoup(resp.text, "html.parser")

    # Find the sidebar
    sidebar = soup.find("div", class_="side") or soup.find("div", class_="sidebar")
    if sidebar:
        sidebar_text = sidebar.get_text(separator=" ")
        emails = _extract_emails(sidebar_text)
        if emails:
            result["email"] = emails[0]
        result["socials"] = _extract_social_handles(sidebar_text, sidebar)

        # Look for Discord links
        for a in sidebar.find_all("a", href=True):
            if "discord" in a["href"].lower():
                result["socials"]["discord"] = a["href"]
                break

    # For Reddit, the "contact" is essentially the modmail
    if not result["email"] and not result["socials"]:
        result["socials"]["reddit_modmail"] = f"https://www.reddit.com/message/compose/?to=/r/{sub_name}"

    logger.info("Reddit r/%s: email=%s, socials=%s", sub_name, result["email"], result["socials"])
    return result


def find_bandcamp_contact(bandcamp_url: str) -> dict:
    """Scrape a Bandcamp artist/label page for contact info."""
    result = {"email": None, "socials": {}, "source": "bandcamp"}

    resp = _get(bandcamp_url)
    if not resp:
        return result

    soup = BeautifulSoup(resp.text, "html.parser")
    page_text = soup.get_text(separator=" ")

    emails = _extract_emails(page_text)
    if emails:
        result["email"] = emails[0]

    result["socials"] = _extract_social_handles(page_text, soup)

    logger.info("Bandcamp %s: email=%s, socials=%s", bandcamp_url, result["email"], result["socials"])
    return result


def find_contact_for_url(url: str) -> dict:
    """Auto-detect platform from URL and find contact info."""
    url_lower = url.lower()

    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return find_youtube_contact(url)
    elif "reddit.com" in url_lower:
        return find_reddit_contact(url)
    elif "bandcamp.com" in url_lower:
        return find_bandcamp_contact(url)
    else:
        # Treat as a generic blog/website
        return find_blog_contact(url)


def enrich_contact(current_contact: str, url: str) -> str:
    """Given a target's existing contact field and its URL, try to find an email.

    Returns the best contact string: email if found, otherwise existing contact.
    """
    # Already has an email — no need to scrape
    if current_contact and "@" in current_contact:
        return current_contact

    info = find_contact_for_url(url)

    # Prefer email
    if info.get("email"):
        return info["email"]

    # Build a social contact string if we found handles
    socials = info.get("socials", {})
    if socials:
        # Prefer DM-able platforms
        for platform in ["instagram", "twitter", "tiktok", "dm_handle", "discord"]:
            if platform in socials:
                return f"{platform}:{socials[platform]}"
        # Fall back to any social
        first = next(iter(socials.items()))
        return f"{first[0]}:{first[1]}"

    # Nothing found — keep existing
    return current_contact or ""
