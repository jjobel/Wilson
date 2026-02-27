"""The Odds API integration — Las Vegas / bookmaker odds for sports markets."""

from __future__ import annotations

import logging
import os
from typing import Optional

import httpx

from kalshi_analyzer.models import Market, MarketCategory, MarketData
from kalshi_analyzer.sources.base import DataSource

logger = logging.getLogger(__name__)

ODDS_API_URL = "https://api.the-odds-api.com/v4"

# Map Kalshi sports categories to Odds API sport keys
# Full list at https://the-odds-api.com/sports-odds-data/sports-apis.html
SPORT_KEYS = [
    "americanfootball_nfl",
    "basketball_nba",
    "baseball_mlb",
    "icehockey_nhl",
    "soccer_usa_mls",
    "tennis_atp_us_open",
    "mma_mixed_martial_arts",
    "boxing_boxing",
]


def _american_to_probability(american_odds: int) -> float:
    """Convert American odds to implied probability."""
    if american_odds >= 0:
        return 100 / (american_odds + 100)
    else:
        return abs(american_odds) / (abs(american_odds) + 100)


class OddsSource(DataSource):
    """Fetches Las Vegas / bookmaker implied probabilities for sports markets."""

    def __init__(self) -> None:
        self._api_key = os.environ.get("ODDS_API_KEY", "")

    @property
    def name(self) -> str:
        return "Vegas Odds"

    def is_available(self) -> bool:
        return bool(self._api_key)

    def enrich(self, market: Market, data: MarketData) -> MarketData:
        """Fetch Vegas odds for sports markets only."""
        if market.category != MarketCategory.SPORTS:
            return data

        query_words = set(market.title.lower().split())
        best_prob = self._find_matching_odds(query_words)

        if best_prob is not None:
            data.vegas_probability = best_prob
            data.data_sources_used.append(self.name)

        return data

    def _find_matching_odds(self, query_words: set[str]) -> Optional[float]:
        """Search across sport keys for a matching event."""
        try:
            with httpx.Client(timeout=20) as client:
                for sport in SPORT_KEYS[:4]:  # Limit API calls — check top 4 sports
                    prob = self._fetch_odds_for_sport(client, sport, query_words)
                    if prob is not None:
                        return prob
        except Exception:
            logger.debug("Odds API error", exc_info=True)
        return None

    def _fetch_odds_for_sport(
        self, client: httpx.Client, sport: str, query_words: set[str]
    ) -> Optional[float]:
        try:
            resp = client.get(
                f"{ODDS_API_URL}/sports/{sport}/odds",
                params={
                    "apiKey": self._api_key,
                    "regions": "us",
                    "markets": "h2h",
                    "oddsFormat": "american",
                },
            )
            if resp.status_code != 200:
                return None

            for event in resp.json():
                home = (event.get("home_team") or "").lower()
                away = (event.get("away_team") or "").lower()
                name_words = set((home + " " + away).split())
                if len(query_words & name_words) >= 2:
                    return self._extract_best_probability(event)
        except Exception:
            logger.debug("Odds fetch failed for %s", sport, exc_info=True)
        return None

    def _extract_best_probability(self, event: dict) -> Optional[float]:
        """Average the home-team probability across all bookmakers."""
        probs: list[float] = []
        for bookmaker in event.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                if market.get("key") != "h2h":
                    continue
                outcomes = market.get("outcomes", [])
                if len(outcomes) >= 1:
                    home_team = event.get("home_team", "")
                    for outcome in outcomes:
                        if outcome.get("name") == home_team:
                            try:
                                odds = int(outcome["price"])
                                probs.append(_american_to_probability(odds))
                            except (KeyError, ValueError):
                                pass
        if not probs:
            return None
        return sum(probs) / len(probs)
