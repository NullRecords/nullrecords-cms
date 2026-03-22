"""Download media files to the local media-library."""

import os
from pathlib import Path

import requests

from app.core.config import get_settings


def download_media(url: str, source: str, filename: str) -> str:
    """Stream-download a file and save it under media-library/{source}/.

    Returns the absolute path of the saved file.
    """
    settings = get_settings()
    dest_dir = Path(settings.media_library_dir) / source
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest_path = dest_dir / filename
    if dest_path.exists():
        return str(dest_path)

    resp = requests.get(url, stream=True, timeout=60)
    resp.raise_for_status()

    with open(dest_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    return str(dest_path)
