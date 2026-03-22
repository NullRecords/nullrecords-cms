"""Media API routes."""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.media import MediaAsset
from app.schemas.media import MediaAssetOut, MediaSearchRequest, MediaSearchResult
from app.services.media.pexels import PexelsSource
from app.services.media.internet_archive import InternetArchiveSource
from app.services.media.downloader import download_media
from app.services.media.tagging import tag_media

router = APIRouter(prefix="/media", tags=["media"])

SOURCES = {
    "pexels": PexelsSource,
    "internet_archive": InternetArchiveSource,
}


@router.post("/search", response_model=list[MediaSearchResult])
def search_media(req: MediaSearchRequest, db: Session = Depends(get_db)):
    """Search a media source and store results in the database."""
    source_cls = SOURCES.get(req.source)
    if source_cls is None:
        raise HTTPException(status_code=400, detail=f"Unknown source: {req.source}")

    source = source_cls()
    raw_results = source.search(req.query)

    output: list[MediaSearchResult] = []
    for raw in raw_results:
        normalized = source.normalize(raw)

        # Upsert: skip if we already have this source+source_id
        existing = (
            db.query(MediaAsset)
            .filter_by(source=normalized["source"], source_id=normalized["source_id"])
            .first()
        )
        if existing is None:
            asset = MediaAsset(**normalized)
            db.add(asset)

        output.append(MediaSearchResult(**normalized))

    db.commit()
    return output


@router.post("/download/{asset_id}", response_model=MediaAssetOut)
def download_asset(asset_id: int, db: Session = Depends(get_db)):
    """Download a media asset to the local media-library."""
    asset = db.query(MediaAsset).filter(MediaAsset.id == asset_id).first()
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    if asset.downloaded and asset.local_path:
        return asset

    if not asset.url:
        raise HTTPException(status_code=400, detail="Asset has no download URL")

    ext = asset.url.rsplit(".", 1)[-1].split("?")[0] if "." in asset.url else "mp4"
    filename = f"{asset.source_id}.{ext}"

    local_path = download_media(asset.url, asset.source, filename)
    asset.local_path = local_path
    asset.downloaded = True
    db.commit()
    db.refresh(asset)
    return asset


@router.post("/tag/{asset_id}", response_model=MediaAssetOut)
def tag_asset(asset_id: int, db: Session = Depends(get_db)):
    """Run AI tagging on a media asset."""
    asset = db.query(MediaAsset).filter(MediaAsset.id == asset_id).first()
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")

    result = tag_media(asset.title)
    asset.tags = json.dumps(result.get("tags", []))
    asset.mood = result.get("mood", "")
    asset.style = result.get("style", "")
    db.commit()
    db.refresh(asset)
    return asset


@router.get("/", response_model=list[MediaAssetOut])
def list_assets(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """List all media assets."""
    return db.query(MediaAsset).offset(skip).limit(limit).all()
