"""System API routes — credential management, health check, contact form."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.credentials import APICredential
from app.schemas.outreach import CredentialCreate, CredentialOut

log = logging.getLogger(__name__)
router = APIRouter(prefix="/system", tags=["system"])


@router.get("/health")
def health_check():
    return {"status": "ok", "service": "ai-engine"}


@router.post("/credential", response_model=CredentialOut)
def store_credential(cred: CredentialCreate, db: Session = Depends(get_db)):
    """Store or update an API credential in the local database."""
    existing = db.query(APICredential).filter_by(service=cred.service).first()
    if existing:
        existing.api_key = cred.api_key
        existing.extra_json = cred.extra_json
        db.commit()
        db.refresh(existing)
        return existing

    new_cred = APICredential(
        service=cred.service,
        api_key=cred.api_key,
        extra_json=cred.extra_json,
    )
    db.add(new_cred)
    db.commit()
    db.refresh(new_cred)
    return new_cred


@router.get("/credentials", response_model=list[CredentialOut])
def list_credentials(db: Session = Depends(get_db)):
    """List all stored credentials (keys are NOT exposed)."""
    return db.query(APICredential).all()


# ── Contact Form ─────────────────────────────────────────────────────────────

CONTACT_LOG = Path(__file__).resolve().parent.parent.parent / "exports" / "contact_submissions.json"


class ContactForm(BaseModel):
    name: str
    email: str
    subject: str
    message: str


@router.post("/contact")
def submit_contact(form: ContactForm):
    """Receive a contact form submission, log it, and email it."""
    entry = {
        "name": form.name,
        "email": form.email,
        "subject": form.subject,
        "message": form.message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Persist to JSON log
    submissions = []
    if CONTACT_LOG.exists():
        try:
            submissions = json.loads(CONTACT_LOG.read_text())
        except (json.JSONDecodeError, ValueError):
            pass
    submissions.append(entry)
    CONTACT_LOG.write_text(json.dumps(submissions, indent=2))
    log.info("Contact form saved: %s <%s> — %s", form.name, form.email, form.subject)

    # Try to email notification
    try:
        from app.services.outreach.email_sender import send_email
        body = (
            f"New contact form submission\n\n"
            f"Name: {form.name}\n"
            f"Email: {form.email}\n"
            f"Subject: {form.subject}\n\n"
            f"{form.message}"
        )
        settings = get_settings()
        to = settings.smtp_from_email or "hello@nullrecords.com"
        send_email(to_address=to, subject=f"[Contact] {form.subject}", body=body)
    except Exception:
        log.exception("Failed to email contact form notification")

    return {"ok": True}
