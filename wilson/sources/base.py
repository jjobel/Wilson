"""Base interface for paper sources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from wilson.models import Paper


class PaperSource(ABC):
    """Abstract base class for all paper/journal sources."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this source."""

    @abstractmethod
    def fetch_recent(self, since: datetime, categories: list[str]) -> list[Paper]:
        """Fetch papers published since the given datetime.

        Args:
            since: Only return papers published after this time.
            categories: Source-specific category identifiers to filter by.

        Returns:
            List of Paper objects matching the criteria.
        """
