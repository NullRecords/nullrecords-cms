"""Brevo CRM integration — sync subscribers to Brevo contacts and send the lead-magnet email.

Uses the Brevo Contacts API (v3) to create/update contacts & manage lists,
and the existing email_sender for transactional lead-magnet delivery.
"""

import logging
from typing import Optional

import requests

from app.core.config import get_settings

logger = logging.getLogger(__name__)

BREVO_CONTACTS_URL = "https://api.brevo.com/v3/contacts"


def _headers() -> dict:
    settings = get_settings()
    return {
        "api-key": settings.smtp_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def sync_contact_to_brevo(email: str, name: Optional[str] = None,
                           source: str = "website") -> Optional[str]:
    """Create or update a contact in Brevo. Returns the Brevo contact ID or None."""
    settings = get_settings()
    if not settings.smtp_key:
        logger.info("Brevo API key not configured — skipping contact sync for %s", email)
        return None

    attributes = {"SOURCE": source}
    if name:
        attributes["FIRSTNAME"] = name.split()[0] if name else ""
        attributes["LASTNAME"] = " ".join(name.split()[1:]) if name and len(name.split()) > 1 else ""

    payload = {
        "email": email,
        "attributes": attributes,
        "updateEnabled": True,
    }

    try:
        resp = requests.post(BREVO_CONTACTS_URL, json=payload, headers=_headers(), timeout=15)
        if resp.status_code in (200, 201, 204):
            data = resp.json() if resp.content else {}
            contact_id = str(data.get("id", ""))
            logger.info("Brevo contact synced: %s (id=%s)", email, contact_id)
            return contact_id
        else:
            logger.warning("Brevo contact sync failed for %s: %s %s",
                           email, resp.status_code, resp.text[:200])
            return None
    except Exception:
        logger.exception("Brevo contact sync error for %s", email)
        return None


def send_lead_magnet_email(email: str, name: Optional[str] = None) -> bool:
    """Send the free lossless track lead-magnet via Brevo transactional API."""
    settings = get_settings()
    if not settings.smtp_key or not settings.smtp_from_email:
        logger.info("Email not configured — cannot send lead magnet to %s", email)
        return False

    greeting = f"Hey {name.split()[0]}" if name else "Hey"

    html_body = f"""
    <div style="font-family: 'Courier New', monospace; background: #0a0a0a; color: #e0e7ff; padding: 2rem; max-width: 600px; margin: 0 auto;">
        <h1 style="color: #00ffff; font-size: 1.5rem;">Your Free Lossless Track</h1>
        <p>{greeting},</p>
        <p>Thanks for joining the NullRecords mailing list! Here's your free lossless WAV track as promised.</p>
        <p style="margin: 1.5rem 0;">
            <a href="https://www.nullrecords.com/store/albums/Oscillator%20Overthruster/hidden%20insite.wav"
               style="display: inline-block; background: #00ff41; color: #0a0a0a; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: bold;">
                Download Free Track (WAV)
            </a>
        </p>
        <p style="color: #888;">This is "Hidden Insite" from the album <em>Oscillating Overthruster</em> by My Evil Robot Army.</p>
        <p>Want the full album in lossless quality? <a href="https://www.nullrecords.com/store/" style="color: #00ffff;">Visit the store</a>.</p>
        <hr style="border-color: #333; margin: 2rem 0;">
        <p style="color: #555; font-size: 0.8rem;">
            You're receiving this because you signed up at nullrecords.com.<br>
            <a href="https://www.nullrecords.com/unsubscribe.html" style="color: #555;">Unsubscribe</a>
        </p>
    </div>
    """

    text_body = (
        f"{greeting},\n\n"
        "Thanks for joining the NullRecords mailing list!\n"
        "Download your free lossless track: "
        "https://www.nullrecords.com/store/albums/Oscillator%20Overthruster/hidden%20insite.wav\n\n"
        "Want the full album? Visit https://www.nullrecords.com/store/\n\n"
        "Unsubscribe: https://www.nullrecords.com/unsubscribe.html"
    )

    payload = {
        "sender": {"email": settings.smtp_from_email, "name": settings.label_name},
        "to": [{"email": email}],
        "subject": "Your Free Lossless Track from NullRecords",
        "htmlContent": html_body,
        "textContent": text_body,
    }

    try:
        resp = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            json=payload,
            headers=_headers(),
            timeout=30,
        )
        resp.raise_for_status()
        logger.info("Lead magnet email sent to %s", email)
        return True
    except Exception:
        logger.exception("Failed to send lead magnet to %s", email)
        return False
