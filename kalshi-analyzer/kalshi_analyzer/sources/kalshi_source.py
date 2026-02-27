"""Kalshi API integration — fetches hot markets and enriches with market data."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from kalshi_analyzer.models import Market, MarketCategory, MarketData
from kalshi_analyzer.sources.base import DataSource

logger = logging.getLogger(__name__)

KALSHI_BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"

# Keyword → category mapping for auto-classification
CATEGORY_KEYWORDS: dict[MarketCategory, list[str]] = {
    MarketCategory.SPORTS: [
        "nfl", "nba", "mlb", "nhl", "nascar", "super bowl", "championship",
        "playoffs", "world series", "stanley cup", "ncaa", "march madness",
        "ufc", "mma", "boxing", "tennis", "golf", "pga", "fifa", "soccer",
        "formula 1", "f1", "olympics", "ufc", "lebron", "curry",
    ],
    MarketCategory.ECONOMICS: [
        "fed", "fomc", "gdp", "cpi", "inflation", "interest rate", "fed funds",
        "unemployment", "jobs report", "nonfarm", "recession", "treasury",
        "bond", "yield", "stock market", "s&p", "dow jones", "nasdaq",
        "bitcoin", "crypto", "ethereum", "oil", "gas price", "dollar",
        "deficit", "debt ceiling", "ipo", "earnings",
    ],
    MarketCategory.POLITICS: [
        "election", "president", "senate", "house", "congress", "vote",
        "democrat", "republican", "trump", "biden", "governor", "mayor",
        "supreme court", "justice", "legislation", "bill", "policy",
        "primary", "ballot", "impeach", "cabinet", "secretary",
    ],
    MarketCategory.ENTERTAINMENT: [
        "oscar", "academy award", "grammy", "emmy", "golden globe",
        "box office", "movie", "film", "streaming", "netflix", "spotify",
        "billboard", "taylor swift", "beyonce", "album", "tour",
        "game show", "reality tv", "celebrity",
    ],
    MarketCategory.WEATHER: [
        "temperature", "hurricane", "tornado", "earthquake", "flood",
        "snow", "blizzard", "heatwave", "drought", "wildfire", "el nino",
        "rainfall", "celsius", "fahrenheit", "climate",
    ],
}


def _detect_category(title: str, tags: list[str]) -> MarketCategory:
    """Classify a market based on its title and tags (no LLM call)."""
    text = (title + " " + " ".join(tags)).lower()
    scores: dict[MarketCategory, int] = {cat: 0 for cat in MarketCategory}
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                scores[category] += 1
    best = max(scores, key=lambda c: scores[c])
    if scores[best] == 0:
        return MarketCategory.GENERAL
    return best


def _parse_market(raw: dict[str, Any], close_cutoff: datetime) -> Market | None:
    """Parse raw Kalshi API market dict into a Market object.

    Returns None if the market is already closed or missing key fields.
    """
    try:
        close_time_str = raw.get("close_time") or raw.get("expiration_time", "")
        if not close_time_str:
            return None
        # Kalshi returns ISO 8601 timestamps
        close_time = datetime.fromisoformat(close_time_str.replace("Z", "+00:00"))
        close_time_naive = close_time.replace(tzinfo=None)

        now = datetime.utcnow()
        if close_time_naive <= now or close_time_naive > close_cutoff:
            return None

        # Prices: Kalshi returns 0–100 (cents), convert to 0–1
        yes_price = raw.get("yes_bid", raw.get("last_price", 50)) / 100.0
        no_price = raw.get("no_bid", 100 - raw.get("last_price", 50)) / 100.0

        # Clamp to valid range
        yes_price = max(0.01, min(0.99, yes_price))
        no_price = max(0.01, min(0.99, no_price))

        ticker = raw.get("ticker", "")
        title = raw.get("title", raw.get("subtitle", ticker))
        tags = raw.get("tags", []) or []
        volume_24h = int(raw.get("volume_24h", raw.get("volume", 0)) or 0)
        open_interest = int(raw.get("open_interest", 0) or 0)

        if not ticker or not title:
            return None

        return Market(
            ticker=ticker,
            title=title,
            category=_detect_category(title, tags),
            yes_price=yes_price,
            no_price=no_price,
            volume_24h=volume_24h,
            open_interest=open_interest,
            close_time=close_time_naive,
            event_ticker=raw.get("event_ticker", ""),
            subtitle=raw.get("subtitle", ""),
            tags=tags,
        )
    except Exception:
        logger.debug("Failed to parse market: %s", raw.get("ticker", "?"), exc_info=True)
        return None


class KalshiSource(DataSource):
    """Fetches Kalshi market data. Handles both discovery and enrichment."""

    BASE_URL = KALSHI_BASE_URL

    def __init__(self, min_volume: int = 100, days_ahead: int = 7) -> None:
        self._min_volume = min_volume
        self._days_ahead = days_ahead
        self._api_key_id = os.environ.get("KALSHI_API_KEY_ID", "")
        self._private_key = os.environ.get("KALSHI_PRIVATE_KEY", "")

    @property
    def name(self) -> str:
        return "Kalshi"

    def is_available(self) -> bool:
        return True  # Public endpoints work without auth

    def _headers(self) -> dict[str, str]:
        headers = {"accept": "application/json"}
        # TODO: Add HMAC auth header when private key is set
        return headers

    def fetch_hot_markets(self) -> list[Market]:
        """Fetch all markets closing within days_ahead, return sorted by volume."""
        close_cutoff = datetime.utcnow() + timedelta(days=self._days_ahead)
        markets: list[Market] = []

        try:
            with httpx.Client(timeout=30) as client:
                cursor = None
                page = 0
                while page < 10:  # cap at 10 pages (500 markets)
                    params: dict[str, Any] = {"limit": 100, "status": "open"}
                    if cursor:
                        params["cursor"] = cursor

                    resp = client.get(
                        f"{self.BASE_URL}/markets",
                        params=params,
                        headers=self._headers(),
                    )
                    resp.raise_for_status()
                    body = resp.json()

                    raw_markets = body.get("markets", [])
                    for raw in raw_markets:
                        m = _parse_market(raw, close_cutoff)
                        if m and m.volume_24h >= self._min_volume:
                            markets.append(m)

                    cursor = body.get("cursor")
                    if not cursor or not raw_markets:
                        break
                    page += 1

        except httpx.HTTPError as exc:
            logger.error("Kalshi API error fetching markets: %s", exc)
            return []

        logger.info("Fetched %d hot markets from Kalshi", len(markets))
        return sorted(markets, key=lambda m: m.volume_24h, reverse=True)

    def enrich(self, market: Market, data: MarketData) -> MarketData:
        """Enrich with current orderbook data (bid/ask spread)."""
        try:
            with httpx.Client(timeout=15) as client:
                resp = client.get(
                    f"{self.BASE_URL}/markets/{market.ticker}",
                    headers=self._headers(),
                )
                if resp.status_code == 200:
                    raw = resp.json().get("market", {})
                    # Refresh prices from live orderbook
                    market.yes_price = max(
                        0.01, min(0.99, raw.get("yes_bid", market.yes_price * 100) / 100.0)
                    )
                    market.no_price = max(
                        0.01, min(0.99, raw.get("no_bid", market.no_price * 100) / 100.0)
                    )
                    data.data_sources_used.append(self.name)
        except Exception:
            logger.debug("Kalshi enrich failed for %s", market.ticker, exc_info=True)
        return data
