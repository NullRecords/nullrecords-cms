"""Marketing dashboard API — reads local dashboard data files for unified reporting."""

import json
import glob
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(prefix="/admin/api/marketing", tags=["marketing"])

# Workspace root (two levels up from ai-engine/app/api/)
WORKSPACE = Path(__file__).resolve().parents[3]
DASHBOARD_DIR = WORKSPACE / "dashboard"
NEWS_FILE = WORKSPACE / "docs" / "news_articles.json"


def _load_json(path: Path):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


@router.get("/overview")
def marketing_overview():
    """Unified marketing dashboard — aggregated from all data sources."""
    contacts = _load_json(DASHBOARD_DIR / "outreach_contacts.json")
    logs = _load_json(DASHBOARD_DIR / "daily_outreach_log.json")
    articles = _load_json(NEWS_FILE)

    # Contact stats
    contact_by_status = {}
    contact_by_type = {}
    for c in contacts:
        status = c.get("status", "unknown")
        ctype = c.get("type", "unknown")
        contact_by_status[status] = contact_by_status.get(status, 0) + 1
        contact_by_type[ctype] = contact_by_type.get(ctype, 0) + 1

    contacted = sum(1 for c in contacts if c.get("contacted_date"))
    responded = sum(1 for c in contacts if c.get("response_received"))

    # Article stats
    article_by_source = {}
    article_by_status = {}
    verified = 0
    for a in articles:
        src = a.get("source", "unknown")
        st = a.get("status", "unknown")
        article_by_source[src] = article_by_source.get(src, 0) + 1
        article_by_status[st] = article_by_status.get(st, 0) + 1
        if st == "verified":
            verified += 1

    # Outreach log trends (last 30 entries)
    recent_logs = logs[-30:] if logs else []
    outreach_trend = []
    for entry in recent_logs:
        outreach_trend.append({
            "date": entry.get("date", "")[:10],
            "contacts_reached": entry.get("contacts_reached", 0),
            "discovery_run": entry.get("discovery_run", False),
        })

    # Daily report count
    report_files = sorted(glob.glob(str(DASHBOARD_DIR / "daily_reports" / "daily_report_*.html")))

    return {
        "contacts": {
            "total": len(contacts),
            "contacted": contacted,
            "responded": responded,
            "response_rate": round(responded / contacted * 100, 1) if contacted else 0,
            "by_status": contact_by_status,
            "by_type": contact_by_type,
        },
        "news": {
            "total_articles": len(articles),
            "verified": verified,
            "needs_verification": article_by_status.get("needs_verification", 0),
            "by_source": article_by_source,
            "by_status": article_by_status,
        },
        "outreach_log": {
            "total_runs": len(logs),
            "trend": outreach_trend,
        },
        "reports": {
            "total_daily_reports": len(report_files),
            "latest": os.path.basename(report_files[-1]) if report_files else None,
        },
    }


@router.get("/contacts")
def list_contacts(limit: int = 50, offset: int = 0):
    """Paginated marketing contacts."""
    contacts = _load_json(DASHBOARD_DIR / "outreach_contacts.json")
    total = len(contacts)
    page = contacts[offset:offset + limit]
    return {
        "total": total,
        "items": [
            {
                "name": c.get("name", ""),
                "type": c.get("type", ""),
                "email": c.get("email"),
                "status": c.get("status", ""),
                "genre_focus": c.get("genre_focus", []),
                "contacted_date": c.get("contacted_date"),
                "response_received": c.get("response_received", False),
                "outreach_count": c.get("outreach_count", 0),
                "confidence_score": c.get("confidence_score", 0),
                "website": c.get("website") or c.get("submission_url") or "",
            }
            for c in page
        ],
    }


@router.get("/news")
def list_news(limit: int = 50, offset: int = 0):
    """Paginated news articles."""
    articles = _load_json(NEWS_FILE)
    total = len(articles)
    page = articles[offset:offset + limit]
    return {
        "total": total,
        "items": [
            {
                "id": a.get("id", ""),
                "title": a.get("title", ""),
                "source": a.get("source", ""),
                "status": a.get("status", ""),
                "article_type": a.get("article_type", ""),
                "sentiment": a.get("sentiment", ""),
                "url": a.get("url", ""),
                "excerpt": a.get("excerpt", "")[:200],
                "discovered_date": a.get("discovered_date"),
                "artist_mentioned": a.get("artist_mentioned", []),
            }
            for a in page
        ],
    }


@router.get("/report-history")
def report_history():
    """Daily report file listing with extracted dates."""
    report_files = sorted(
        glob.glob(str(DASHBOARD_DIR / "daily_reports" / "daily_report_*.html")),
        reverse=True,
    )
    reports = []
    for path in report_files[:60]:
        name = os.path.basename(path)
        # Extract date from filename: daily_report_2025-09-10.html or daily_report_20251230_080006.html
        m = re.search(r"(\d{4}[-_]?\d{2}[-_]?\d{2})", name)
        date_str = m.group(1) if m else name
        size = os.path.getsize(path)
        reports.append({"filename": name, "date": date_str, "size_kb": round(size / 1024, 1)})
    return {"total": len(report_files), "reports": reports}


@router.get("/trends")
def dashboard_trends():
    """Historical trend data extracted from daily reports and outreach logs.

    Returns time-series suitable for charting.
    """
    contacts = _load_json(DASHBOARD_DIR / "outreach_contacts.json")
    logs = _load_json(DASHBOARD_DIR / "daily_outreach_log.json")
    articles = _load_json(NEWS_FILE)

    # Outreach timeline
    outreach_timeline = []
    for entry in logs:
        outreach_timeline.append({
            "date": entry.get("date", "")[:10],
            "contacts_reached": entry.get("contacts_reached", 0),
        })

    # Contact acquisition over time
    contact_timeline = {}
    for c in contacts:
        d = (c.get("discovered_date") or c.get("contacted_date") or "")[:10]
        if d:
            contact_timeline[d] = contact_timeline.get(d, 0) + 1
    contact_dates = sorted(contact_timeline.items())

    # Articles discovered over time
    article_timeline = {}
    for a in articles:
        d = (a.get("discovered_date") or "")[:10]
        if d:
            article_timeline[d] = article_timeline.get(d, 0) + 1
    article_dates = sorted(article_timeline.items())

    # Contact type distribution
    type_dist = {}
    for c in contacts:
        t = c.get("type", "unknown")
        type_dist[t] = type_dist.get(t, 0) + 1

    # News source distribution
    source_dist = {}
    for a in articles:
        s = a.get("source", "unknown")
        source_dist[s] = source_dist.get(s, 0) + 1

    # Status funnel
    status_funnel = {}
    for c in contacts:
        s = c.get("status", "unknown")
        status_funnel[s] = status_funnel.get(s, 0) + 1

    return {
        "outreach_timeline": outreach_timeline,
        "contact_acquisition": [{"date": d, "count": n} for d, n in contact_dates],
        "article_discovery": [{"date": d, "count": n} for d, n in article_dates],
        "contact_type_distribution": type_dist,
        "news_source_distribution": source_dist,
        "status_funnel": status_funnel,
    }
