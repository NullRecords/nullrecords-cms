"""Configuration module — loads environment variables and sets project paths."""

import os
from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings


# Root of the ai-engine project (parent of /app)
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    # --- Database ---
    database_url: str = f"sqlite:///{BASE_DIR / 'ai_engine.db'}"

    # --- OpenAI ---
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # --- Pexels ---
    pexels_api_key: str = ""

    # --- Spotify ---
    spotify_client_id: str = ""
    spotify_client_secret: str = ""

    # --- YouTube ---
    youtube_api_key: str = ""
    youtube_client_id: str = ""
    youtube_client_secret: str = ""

    # --- Paths ---
    media_library_dir: str = str(BASE_DIR / "media-library")
    exports_dir: str = str(BASE_DIR / "exports")

    # --- Label metadata (used for outreach scoring) ---
    label_genre: str = "nu jazz, experimental electronic"
    label_name: str = "NullRecords"

    model_config = {"env_file": str(BASE_DIR / ".env"), "env_file_encoding": "utf-8"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
