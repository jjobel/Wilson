"""Shared data models for the Kalshi bet analyzer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class MarketCategory(str, Enum):
    SPORTS = "sports"
    ECONOMICS = "economics"
    POLITICS = "politics"
    ENTERTAINMENT = "entertainment"
    WEATHER = "weather"
    GENERAL = "general"


class Confidence(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


@dataclass
class Market:
    """A single Kalshi prediction market."""

    ticker: str
    title: str
    category: MarketCategory
    yes_price: float  # 0.0–1.0 (implied probability of YES)
    no_price: float   # 0.0–1.0 (implied probability of NO)
    volume_24h: int
    open_interest: int
    close_time: datetime
    event_ticker: str = ""
    subtitle: str = ""
    tags: list[str] = field(default_factory=list)

    def implied_probability(self) -> float:
        """Return the YES implied probability (same as yes_price)."""
        return self.yes_price

    def days_remaining(self) -> float:
        """Return days until market closes. Returns 0.0 if already closed."""
        delta = self.close_time - datetime.utcnow()
        return max(0.0, delta.total_seconds() / 86400)

    def format_price(self) -> str:
        return f"{self.yes_price:.0%} YES / {self.no_price:.0%} NO"


@dataclass
class NewsArticle:
    """A single news article with sentiment score."""

    title: str
    source: str
    published: datetime
    url: str
    snippet: str
    sentiment_score: float = 0.0  # VADER compound: -1.0 to +1.0


@dataclass
class MarketData:
    """Enriched market data aggregated from all sources."""

    market: Market

    # News
    news_articles: list[NewsArticle] = field(default_factory=list)
    gdelt_tone: Optional[float] = None  # GDELT average tone

    # Sentiment
    reddit_sentiment: Optional[float] = None   # VADER compound avg from Reddit
    twitter_sentiment: Optional[float] = None  # VADER compound avg from X/Twitter

    # Cross-market comparison
    polymarket_probability: Optional[float] = None  # Polymarket YES probability

    # Sports odds (for SPORTS category markets)
    vegas_probability: Optional[float] = None       # Implied probability from bookmakers

    # Financial context (for ECONOMICS category markets)
    yfinance_context: str = ""

    # Final estimate synthesized from all sources (set by AnalysisEngine)
    estimated_probability: Optional[float] = None

    # Which sources successfully contributed data
    data_sources_used: list[str] = field(default_factory=list)

    def aggregate_sentiment(self) -> Optional[float]:
        """Weighted average of all available sentiment signals (-1 to +1)."""
        scores = []
        if self.reddit_sentiment is not None:
            scores.append(self.reddit_sentiment)
        if self.twitter_sentiment is not None:
            scores.append(self.twitter_sentiment)
        if self.gdelt_tone is not None:
            # GDELT tone is roughly -100 to +100; normalize to -1/+1
            scores.append(max(-1.0, min(1.0, self.gdelt_tone / 10.0)))
        # News articles inline sentiment
        if self.news_articles:
            news_avg = sum(a.sentiment_score for a in self.news_articles) / len(self.news_articles)
            scores.append(news_avg)
        if not scores:
            return None
        return sum(scores) / len(scores)


@dataclass
class ScoreBreakdown:
    """Per-dimension scores for a recommendation (all 0.0–1.0)."""

    edge_score: float = 0.0          # |estimated_prob - market_price| / 0.20, capped at 1
    sentiment_alignment: float = 0.0 # Sentiment direction agrees with recommended position
    market_consensus: float = 0.0    # Polymarket alignment
    vegas_alignment: float = 0.0     # Vegas odds alignment (sports only)
    liquidity_score: float = 0.0     # Inverse of volume (low vol = more edge opportunity)
    time_sensitivity: float = 0.0    # Urgency of the bet (closer = higher)
    composite_score: float = 0.0     # Weighted composite


@dataclass
class Recommendation:
    """A single bet recommendation with full supporting evidence."""

    market: Market
    position: str          # "YES" or "NO"
    confidence: Confidence
    estimated_probability: float
    edge: float            # signed: positive = we expect YES to be underpriced
    score_breakdown: ScoreBreakdown
    evidence_bullets: list[str] = field(default_factory=list)
    risk_warnings: list[str] = field(default_factory=list)
    analysis_text: str = ""

    def format_display(self) -> str:
        """Return a compact single-line summary."""
        edge_str = f"+{self.edge:.0%}" if self.edge >= 0 else f"{self.edge:.0%}"
        return (
            f"[{self.position}] {self.market.ticker}  "
            f"Kalshi: {self.market.yes_price:.0%}  "
            f"Est: {self.estimated_probability:.0%}  "
            f"Edge: {edge_str}  "
            f"Conf: {self.confidence.value}"
        )
