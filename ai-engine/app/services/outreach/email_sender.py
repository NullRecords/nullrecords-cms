"""Email delivery via Brevo Transactional API (preferred) or SMTP fallback.

Brevo API provides message IDs for delivery/open/click tracking.
When neither is configured, messages are logged instead of sent.
"""

import logging
import smtplib
from email.mime.text import MIMEText
from typing import Optional

import requests

from app.core.config import get_settings

logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def send_email(
    to_address: str,
    subject: str,
    body: str,
    tracking_pixel_url: Optional[str] = None,
) -> dict:
    """Send an email. Returns {"sent": bool, "message_id": str|None, "method": str}.

    Tries Brevo Transactional API first (gives us a messageId for tracking).
    Falls back to SMTP if no Brevo API key. Logs if neither is configured.
    """
    settings = get_settings()

    # ── Try Brevo Transactional API first ──
    if settings.smtp_key and settings.smtp_from_email:
        return _send_via_brevo_api(to_address, subject, body, tracking_pixel_url, settings)

    # ── SMTP fallback (no tracking ID) ──
    if settings.smtp_host and settings.smtp_from_email:
        return _send_via_smtp(to_address, subject, body, settings)

    # ── Not configured — log only ──
    logger.info(
        "Email not configured — logging instead. To: %s Subject: %s", to_address, subject
    )
    return {"sent": False, "message_id": None, "method": "logged"}


def _send_via_brevo_api(
    to_address: str,
    subject: str,
    body: str,
    tracking_pixel_url: Optional[str],
    settings,
) -> dict:
    """Send via Brevo Transactional Email API. Returns message ID for tracking."""
    # Build HTML body with optional tracking pixel
    html_body = f"<div style='font-family:sans-serif;line-height:1.6'>{_text_to_html(body)}</div>"
    if tracking_pixel_url:
        html_body += f'<img src="{tracking_pixel_url}" width="1" height="1" alt="" style="display:none" />'

    payload = {
        "sender": {"email": settings.smtp_from_email, "name": settings.label_name},
        "to": [{"email": to_address}],
        "subject": subject,
        "htmlContent": html_body,
        "textContent": body,
    }
    headers = {
        "api-key": settings.smtp_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        resp = requests.post(BREVO_API_URL, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        message_id = data.get("messageId", "")
        logger.info("Brevo API sent to %s — messageId: %s", to_address, message_id)
        return {"sent": True, "message_id": message_id, "method": "brevo_api"}
    except requests.RequestException:
        logger.exception("Brevo API failed for %s — falling back to SMTP", to_address)
        # fall through to SMTP
        return _send_via_smtp(to_address, subject, body, settings)


def _send_via_smtp(to_address: str, subject: str, body: str, settings) -> dict:
    """Send via raw SMTP. No tracking ID available."""
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from_email
    msg["To"] = to_address

    password = settings.smtp_key or settings.smtp_password

    try:
        if settings.smtp_use_tls:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
                server.starttls()
                if settings.smtp_user and password:
                    server.login(settings.smtp_user, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
                if settings.smtp_user and password:
                    server.login(settings.smtp_user, password)
                server.send_message(msg)
        logger.info("SMTP sent to %s: %s", to_address, subject)
        return {"sent": True, "message_id": None, "method": "smtp"}
    except Exception:
        logger.exception("SMTP failed for %s", to_address)
        return {"sent": False, "message_id": None, "method": "smtp_failed"}


def _text_to_html(text: str) -> str:
    """Convert plain text to simple HTML paragraphs."""
    import html
    paragraphs = text.strip().split("\n\n")
    return "".join(f"<p>{html.escape(p).replace(chr(10), '<br>')}</p>" for p in paragraphs)
