"""Background job scheduler using APScheduler.

Manages three automated pipelines:
  1. Follow-up execution — checks for due follow-ups, regenerates messages, attempts delivery
  2. Source discovery — periodic scraping of Bandcamp/SoundCloud/YouTube/Reddit
  3. Media ingestion — searches configured sources and downloads + tags new assets
"""

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


# ── Job implementations ─────────────────────────────────────────────────


def _run_pending_followups():
    """Check for due follow-ups, regenerate messages, and attempt delivery."""
    from app.core.database import SessionLocal
    from app.models.outreach import OutreachLog
    from app.models.playlist import Playlist
    from app.models.influencer import Influencer
    from app.services.outreach.followup import get_pending_followups, schedule_follow_up
    from app.services.outreach.messaging import generate_outreach_message
    from app.services.outreach.email_sender import send_email

    settings = get_settings()
    db = SessionLocal()
    try:
        due = get_pending_followups(db)
        if not due:
            logger.info("No follow-ups due at %s", datetime.now(timezone.utc).isoformat())
            return

        for log in due:
            # Look up target details for message context
            if log.target_type == "playlist":
                target = db.query(Playlist).filter(Playlist.id == log.target_id).first()
                name = target.name if target else f"playlist-{log.target_id}"
                contact = (target.contact if target else "") or ""
                context = (
                    f"Follow-up — playlist with {target.followers} followers, "
                    f"curated by {target.curator_name}"
                ) if target else "Follow-up"
            else:
                target = db.query(Influencer).filter(Influencer.id == log.target_id).first()
                name = target.handle if target else f"influencer-{log.target_id}"
                contact = (target.contact if target else "") or ""
                context = (
                    f"Follow-up — {target.platform} creator in {target.niche} "
                    f"with {target.followers} followers"
                ) if target else "Follow-up"

            # Generate a fresh follow-up message
            message = generate_outreach_message(name, log.target_type, context)
            subject = f"Following up — {settings.label_name}"

            # Attempt email delivery if we have an email-like contact
            result = {"sent": False, "message_id": None, "method": "logged"}
            if contact and "@" in contact:
                result = send_email(contact, subject, message)

            # Update the outreach log
            log.message = message
            log.subject = subject
            log.status = "sent" if result["sent"] else "follow_up_logged"
            log.message_id = result.get("message_id")
            log.follow_up_date = None  # clear so it isn't picked up again
            db.commit()

            logger.info(
                "Follow-up processed: outreach_id=%d target=%s/%d method=%s",
                log.id, log.target_type, log.target_id, result["method"],
            )

            # Auto-schedule next follow-up (in 7 days)
            schedule_follow_up(db, log.id, days=7)

    except Exception:
        logger.exception("Error in follow-up job")
    finally:
        db.close()


def _run_discovery():
    """Periodically discover new playlists and influencers."""
    from app.core.database import SessionLocal
    from app.models.playlist import Playlist
    from app.models.influencer import Influencer
    from app.services.outreach.discovery import discover_playlists, discover_influencers
    from app.services.outreach.scoring import score_relevance

    settings = get_settings()
    query = settings.scheduler_discovery_query
    db = SessionLocal()
    try:
        logger.info("Running scheduled discovery for: %s", query)
        playlists_raw = discover_playlists(query)
        influencers_raw = discover_influencers(query)

        playlists_added = 0
        for p in playlists_raw:
            existing = db.query(Playlist).filter_by(
                name=p["name"], platform=p["platform"]
            ).first()
            if existing:
                continue
            relevance = score_relevance(p["name"], p.get("curator_name", ""))
            pl = Playlist(
                name=p["name"],
                platform=p["platform"],
                curator_name=p.get("curator_name", ""),
                followers=p.get("followers", 0),
                contact=p.get("contact", ""),
                url=p.get("url", ""),
                relevance_score=relevance,
            )
            db.add(pl)
            playlists_added += 1

        influencers_added = 0
        for i in influencers_raw:
            existing = db.query(Influencer).filter_by(
                handle=i["handle"], platform=i["platform"]
            ).first()
            if existing:
                continue
            relevance = score_relevance(i["handle"], i.get("niche", ""))
            inf = Influencer(
                handle=i["handle"],
                platform=i["platform"],
                followers=i.get("followers", 0),
                niche=i.get("niche", ""),
                contact=i.get("contact", ""),
                relevance_score=relevance,
            )
            db.add(inf)
            influencers_added += 1

        db.commit()
        logger.info(
            "Discovery complete — %d new playlists, %d new influencers",
            playlists_added, influencers_added,
        )
    except Exception:
        logger.exception("Error in discovery job")
    finally:
        db.close()


def _run_media_ingest():
    """Search configured sources, download new assets, and tag them."""
    from pathlib import Path
    from app.core.database import SessionLocal
    from app.models.media import MediaAsset
    from app.services.media.pexels import PexelsSource
    from app.services.media.internet_archive import InternetArchiveSource
    from app.services.media.downloader import download_media
    from app.services.media.tagging import tag_media

    settings = get_settings()
    query = settings.scheduler_discovery_query
    sources = [
        ("pexels", PexelsSource()),
        ("internet_archive", InternetArchiveSource()),
    ]

    db = SessionLocal()
    try:
        total_new = 0
        total_downloaded = 0
        total_tagged = 0

        for source_name, source in sources:
            logger.info("Media ingest: searching %s for '%s'", source_name, query)
            try:
                raw_results = source.search(query)
            except Exception:
                logger.exception("Search failed for %s", source_name)
                continue

            for raw in raw_results:
                normalized = source.normalize(raw)
                existing = (
                    db.query(MediaAsset)
                    .filter_by(source=normalized["source"], source_id=normalized["source_id"])
                    .first()
                )
                if existing:
                    continue

                asset = MediaAsset(**normalized)
                db.add(asset)
                db.flush()
                total_new += 1

                # Auto-download if URL available
                if asset.url:
                    try:
                        url_path = asset.url.rsplit("?", 1)[0]
                        ext = Path(url_path).suffix.lstrip(".") if Path(url_path).suffix else "mp4"
                        if len(ext) > 5 or "/" in ext:
                            ext = "mp4"
                        filename = f"{asset.source_id}.{ext}"
                        local_path = download_media(asset.url, asset.source, filename)
                        asset.local_path = local_path
                        asset.downloaded = True
                        total_downloaded += 1
                    except Exception:
                        logger.exception("Download failed for asset %s", asset.source_id)

                # Auto-tag if downloaded
                if asset.downloaded and asset.local_path:
                    try:
                        tags = tag_media(asset.local_path, asset.title or "")
                        asset.tags = ",".join(tags) if isinstance(tags, list) else str(tags)
                        total_tagged += 1
                    except Exception:
                        logger.exception("Tagging failed for asset %s", asset.source_id)

        db.commit()
        logger.info(
            "Media ingest complete — %d new, %d downloaded, %d tagged",
            total_new, total_downloaded, total_tagged,
        )
    except Exception:
        logger.exception("Error in media ingest job")
    finally:
        db.close()


# ── Scheduler lifecycle ──────────────────────────────────────────────────


def _run_campaign_reminder():
    """Log today's campaign posts — acts as a daily content prompt."""
    import json
    from pathlib import Path

    campaign_file = Path(__file__).resolve().parents[1] / "static" / "presave_campaign.json"
    if not campaign_file.exists():
        logger.info("No campaign file found — skipping")
        return

    with open(campaign_file) as f:
        data = json.load(f)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for post in data.get("daily_posts", []):
        if post.get("day") == today:
            posted = post.get("posted", {})
            platforms = [p for p in ("tiktok", "instagram", "youtube", "twitter_x") if p in post]
            pending = [p for p in platforms if p not in posted]
            if pending:
                logger.info(
                    "CAMPAIGN REMINDER — %s | Theme: %s | Pending platforms: %s",
                    data.get("campaign", "?"),
                    post.get("theme", "?"),
                    ", ".join(pending),
                )
            else:
                logger.info("All campaign posts for today are marked as posted")
            return

    logger.info("No campaign posts scheduled for %s", today)


def _has_actionable_contact(contact: str) -> bool:
    """Check if a contact string is something we can actually send to."""
    if not contact:
        return False
    if "@" in contact:
        return True
    if ":" in contact and any(p in contact.lower() for p in ["instagram", "twitter", "tiktok", "discord"]):
        return True
    return False


def _run_contact_enrichment():
    """Scrape web pages to find email/social contacts for targets missing them."""
    from app.core.database import SessionLocal
    from app.models.playlist import Playlist
    from app.models.influencer import Influencer
    from app.services.outreach.contact_finder import enrich_contact

    db = SessionLocal()
    try:
        enriched = 0
        checked = 0

        # Enrich playlists
        playlists = db.query(Playlist).all()
        for p in playlists:
            if _has_actionable_contact(p.contact):
                continue
            if not p.url:
                continue
            checked += 1
            try:
                new_contact = enrich_contact(p.contact or "", p.url)
                if new_contact and new_contact != (p.contact or ""):
                    p.contact = new_contact
                    enriched += 1
                    logger.info("Enriched playlist %s: %s", p.name, new_contact)
            except Exception:
                logger.exception("Failed to enrich playlist %s", p.name)

        # Enrich influencers
        influencers = db.query(Influencer).all()
        for i in influencers:
            if _has_actionable_contact(i.contact):
                continue
            url = i.contact if i.contact and i.contact.startswith("http") else ""
            if not url:
                continue
            checked += 1
            try:
                new_contact = enrich_contact("", url)
                if new_contact and new_contact != (i.contact or ""):
                    i.contact = new_contact
                    enriched += 1
                    logger.info("Enriched influencer %s: %s", i.handle, new_contact)
            except Exception:
                logger.exception("Failed to enrich influencer %s", i.handle)

        db.commit()
        logger.info(
            "Contact enrichment complete — checked %d, enriched %d",
            checked, enriched,
        )
    except Exception:
        logger.exception("Error in contact enrichment job")
    finally:
        db.close()


def _run_news_search():
    """Search the web for mentions of NullRecords and My Evil Robot Army."""
    import json
    from pathlib import Path
    from app.services.outreach.news_search import search_news

    settings = get_settings()
    try:
        results = search_news(youtube_api_key=settings.youtube_api_key)

        workspace = Path(__file__).resolve().parents[3]
        news_file = workspace / "docs" / "news_articles.json"
        try:
            existing = json.loads(news_file.read_text()) if news_file.exists() else []
        except (json.JSONDecodeError, OSError):
            existing = []

        existing_urls = {a.get("url", "") for a in existing}
        new_count = 0
        for r in results:
            if r["url"] in existing_urls:
                continue
            existing.append(r)
            existing_urls.add(r["url"])
            new_count += 1

        if new_count > 0:
            news_file.write_text(json.dumps(existing, indent=2, default=str))

        logger.info(
            "News search complete — %d results, %d new articles saved (total: %d)",
            len(results), new_count, len(existing),
        )
    except Exception:
        logger.exception("Error in news search job")


def _run_dj_radio_discovery():
    """Discover DJs, radio stations, and shows for outreach."""
    from app.core.database import SessionLocal
    from app.models.influencer import Influencer
    from app.services.outreach.dj_radio_discovery import discover_dj_radio
    from app.services.outreach.scoring import score_relevance

    db = SessionLocal()
    try:
        raw = discover_dj_radio()
        added = 0
        for r in raw:
            existing = db.query(Influencer).filter_by(
                handle=r["handle"], platform=r["platform"]
            ).first()
            if existing:
                continue
            relevance = score_relevance(r["handle"], r.get("niche", ""))
            inf = Influencer(
                handle=r["handle"],
                platform=r["platform"],
                followers=r.get("followers", 0),
                niche=r.get("niche", ""),
                contact=r.get("contact", ""),
                relevance_score=relevance,
            )
            db.add(inf)
            added += 1

        db.commit()
        logger.info("DJ/Radio discovery complete — %d discovered, %d new added", len(raw), added)
    except Exception:
        logger.exception("Error in DJ/radio discovery job")
    finally:
        db.close()


def _run_auto_outreach():
    """Send outreach to high-scoring uncontacted targets with actionable contacts only."""
    from app.core.database import SessionLocal
    from app.models.playlist import Playlist
    from app.models.influencer import Influencer
    from app.models.outreach import OutreachLog
    from app.services.outreach.messaging import generate_outreach_message
    from app.services.outreach.followup import schedule_follow_up
    from app.services.outreach.email_sender import send_email

    settings = get_settings()
    min_score = settings.auto_outreach_min_score
    max_per_run = settings.auto_outreach_max_per_run
    db = SessionLocal()
    try:
        targets = []

        # Find uncontacted playlists above threshold
        playlists = (
            db.query(Playlist)
            .filter(
                Playlist.relevance_score >= min_score,
                Playlist.last_contacted.is_(None),
            )
            .order_by(Playlist.relevance_score.desc())
            .limit(max_per_run * 2)  # fetch extra since some may lack contacts
            .all()
        )
        for p in playlists:
            if not _has_actionable_contact(p.contact or ""):
                continue
            if len(targets) >= max_per_run:
                break
            targets.append(("playlist", p.id, p.name, p.contact or "",
                f"Playlist with {p.followers} followers, curated by {p.curator_name}"))

        # Find uncontacted influencers above threshold
        remaining = max_per_run - len(targets)
        if remaining > 0:
            influencers = (
                db.query(Influencer)
                .filter(
                    Influencer.relevance_score >= min_score,
                    Influencer.last_contacted.is_(None),
                )
                .order_by(Influencer.relevance_score.desc())
                .limit(remaining * 2)
                .all()
            )
            for i in influencers:
                if not _has_actionable_contact(i.contact or ""):
                    continue
                if len(targets) >= max_per_run:
                    break
                targets.append(("influencer", i.id, i.handle, i.contact or "",
                    f"{i.platform} creator in {i.niche} with {i.followers} followers"))

        if not targets:
            logger.info("Auto-outreach: no contactable uncontacted targets above %.1f score", min_score)
            return

        sent = 0
        skipped = 0
        for target_type, target_id, name, contact, context in targets:
            message = generate_outreach_message(name, target_type, context)
            subject = f"Hello from {settings.label_name}"

            result = {"sent": False, "message_id": None, "method": "logged"}
            if contact and "@" in contact:
                result = send_email(contact, subject, message)
            else:
                # Social-only contacts — log for manual DM
                skipped += 1

            log = OutreachLog(
                target_type=target_type,
                target_id=target_id,
                message=message,
                subject=subject,
                status="sent" if result["sent"] else "needs_dm",
                message_id=result.get("message_id"),
            )
            db.add(log)
            db.flush()

            # Mark contacted
            if target_type == "playlist":
                t = db.query(Playlist).get(target_id)
            else:
                t = db.query(Influencer).get(target_id)
            if t:
                t.last_contacted = datetime.now(timezone.utc)

            schedule_follow_up(db, log.id, days=5)

            if result["sent"]:
                sent += 1

        db.commit()
        logger.info(
            "Auto-outreach complete — %d emailed, %d need manual DM (score >= %.1f)",
            sent, skipped, min_score,
        )
    except Exception:
        logger.exception("Error in auto-outreach job")
    finally:
        db.close()



def start_scheduler():
    """Create and start the APScheduler background scheduler."""
    global _scheduler
    settings = get_settings()

    if not settings.scheduler_enabled:
        logger.info("Scheduler disabled via config")
        return

    if _scheduler and _scheduler.running:
        logger.warning("Scheduler already running")
        return

    _scheduler = BackgroundScheduler(
        job_defaults={"coalesce": True, "max_instances": 1},
    )

    _scheduler.add_job(
        _run_pending_followups,
        trigger=IntervalTrigger(minutes=settings.scheduler_followup_minutes),
        id="followup_check",
        name="Check & execute due follow-ups",
        replace_existing=True,
    )

    _scheduler.add_job(
        _run_discovery,
        trigger=IntervalTrigger(hours=settings.scheduler_discovery_hours),
        id="source_discovery",
        name="Discover new playlists & influencers",
        replace_existing=True,
    )

    _scheduler.add_job(
        _run_media_ingest,
        trigger=IntervalTrigger(hours=settings.scheduler_media_ingest_hours),
        id="media_ingest",
        name="Search, download & tag new media",
        replace_existing=True,
    )

    _scheduler.add_job(
        _run_campaign_reminder,
        trigger=IntervalTrigger(hours=8),
        id="campaign_reminder",
        name="Check campaign posts for today",
        replace_existing=True,
    )

    _scheduler.add_job(
        _run_auto_outreach,
        trigger=IntervalTrigger(hours=settings.auto_outreach_interval_hours),
        id="auto_outreach",
        name="Auto-outreach to uncontacted high-score targets",
        replace_existing=True,
    )

    _scheduler.add_job(
        _run_contact_enrichment,
        trigger=IntervalTrigger(hours=6),
        id="contact_enrichment",
        name="Find emails & social handles for targets",
        replace_existing=True,
    )

    _scheduler.add_job(
        _run_news_search,
        trigger=IntervalTrigger(hours=12),
        id="news_search",
        name="Search web for NullRecords/MERA mentions",
        replace_existing=True,
    )

    _scheduler.add_job(
        _run_dj_radio_discovery,
        trigger=IntervalTrigger(hours=48),
        id="dj_radio_discovery",
        name="Discover DJs, radio stations & shows",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info(
        "Scheduler started — followups every %dm, discovery every %dh, "
        "media ingest every %dh, news search every 12h, DJ/radio every 48h",
        settings.scheduler_followup_minutes,
        settings.scheduler_discovery_hours,
        settings.scheduler_media_ingest_hours,
    )


def stop_scheduler():
    """Shut down the scheduler gracefully."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
    _scheduler = None


def get_scheduler_status() -> dict:
    """Return current scheduler status and job info."""
    if not _scheduler or not _scheduler.running:
        return {"running": False, "jobs": []}

    jobs = []
    for job in _scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger),
        })
    return {"running": True, "jobs": jobs}


def trigger_job(job_id: str) -> bool:
    """Manually trigger a scheduled job to run immediately."""
    if not _scheduler or not _scheduler.running:
        return False

    job = _scheduler.get_job(job_id)
    if not job:
        return False

    job.modify(next_run_time=datetime.now(timezone.utc))
    return True

