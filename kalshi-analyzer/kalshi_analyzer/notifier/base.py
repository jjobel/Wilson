"""Notifier protocol — all notification backends must implement this interface."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from kalshi_analyzer.models import MarketData, Recommendation


@runtime_checkable
class Notifier(Protocol):
    """Delivers analysis results to the user."""

    def send(
        self,
        recommendations: list[Recommendation],
        market_data_list: list[MarketData],
    ) -> None:
        """Send the top recommendations and supporting market data."""
        ...
