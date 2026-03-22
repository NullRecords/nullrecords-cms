"""System API routes — credential management and health check."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.credentials import APICredential
from app.schemas.outreach import CredentialCreate, CredentialOut

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
