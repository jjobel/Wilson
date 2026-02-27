"""Abstract base class for all data enrichment sources."""

from __future__ import annotations

from abc import ABC, abstractmethod

from kalshi_analyzer.models import Market, MarketData


class DataSource(ABC):
    """Protocol for sources that enrich a MarketData bag with external data."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this source."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the source can be used (API keys present, etc.).

        Sources that return False are silently skipped during enrichment.
        """
        ...

    @abstractmethod
    def enrich(self, market: Market, data: MarketData) -> MarketData:
        """Enrich the MarketData with data from this source.

        Implementations should:
        - Set the relevant fields on `data` in-place and return it
        - Append self.name to data.data_sources_used on success
        - Catch and log all exceptions rather than propagating them
        """
        ...
