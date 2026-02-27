"""Polymarket API integration — cross-market probability comparison."""

from __future__ import annotations

import logging

import httpx

from kalshi_analyzer.models import Market, MarketData
from kalshi_analyzer.sources.base import DataSource

logger = logging.getLogger(__name__)

POLYMARKET_GAMMA_URL = "https://gamma-api.polymarket.com"


class PolymarketSource(DataSource):
    """Fetches Polymarket implied probability for markets matching Kalshi events."""

    @property
    def name(self) -> str:
        return "Polymarket"

    def is_available(self) -> bool:
        return True  # No auth required

    def enrich(self, market: Market, data: MarketData) -> MarketData:
        """Search Polymarket for a matching market and extract its price."""
        # Build a short keyword query from the market title
        query = " ".join(market.title.split()[:6])
        try:
            with httpx.Client(timeout=15) as client:
                resp = client.get(
                    f"{POLYMARKET_GAMMA_URL}/markets",
                    params={"q": query, "limit": 5, "active": "true"},
                )
                if resp.status_code != 200:
                    return data

                results = resp.json()
                if not isinstance(results, list) or not results:
                    return data

                # Pick the best match: highest string similarity to Kalshi title
                best = _best_match(market.title, results)
                if best is None:
                    return data

                # Polymarket outcomePrices is a JSON string e.g. "[0.63, 0.37]"
                prices_raw = best.get("outcomePrices")
                if isinstance(prices_raw, str):
                    import json
                    prices = json.loads(prices_raw)
                elif isinstance(prices_raw, list):
                    prices = prices_raw
                else:
                    return data

                if prices:
                    # prices[0] is YES price for binary markets
                    data.polymarket_probability = float(prices[0])
                    data.data_sources_used.append(self.name)

        except Exception:
            logger.debug("Polymarket enrich failed for %s", market.ticker, exc_info=True)

        return data


def _best_match(title: str, results: list[dict]) -> dict | None:
    """Return the Polymarket market with the highest word overlap to title."""
    title_words = set(title.lower().split())
    best_score = 0
    best_result = None
    for r in results:
        question = r.get("question", "").lower()
        overlap = len(title_words & set(question.split()))
        if overlap > best_score:
            best_score = overlap
            best_result = r
    # Require at least 2 overlapping words to avoid false matches
    return best_result if best_score >= 2 else None
