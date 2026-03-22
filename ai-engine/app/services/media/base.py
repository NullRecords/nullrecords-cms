"""Abstract base class for all media source plugins."""

from abc import ABC, abstractmethod
from typing import Any


class MediaSource(ABC):
    """Every media source plugin must implement search() and normalize()."""

    source_name: str = "unknown"

    @abstractmethod
    def search(self, query: str, per_page: int = 10) -> list[dict[str, Any]]:
        """Query the external source and return raw results."""

    @abstractmethod
    def normalize(self, result: dict[str, Any]) -> dict[str, Any]:
        """Convert a single raw result into the common schema:

        {
            "source": str,
            "source_id": str,
            "title": str,
            "url": str,
            "preview_url": str,
            "duration": float,
        }
        """
