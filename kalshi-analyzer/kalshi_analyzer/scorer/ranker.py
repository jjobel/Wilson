"""Two-stage ranking: hot market filter → composite score after enrichment."""

from __future__ import annotations

import logging
from typing import Optional

from kalshi_analyzer.models import (
    Confidence,
    Market,
    MarketData,
    Recommendation,
    ScoreBreakdown,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Stage 1: Hot market score (Kalshi data only)
# ---------------------------------------------------------------------------

def rank_hot_markets(
    markets: list[Market],
    top_n: int = 20,
    weights: Optional[dict[str, float]] = None,
) -> list[Market]:
    """Score and rank markets by activity/uncertainty. Returns top_n candidates."""
    if not markets:
        return []

    w = weights or {
        "volume": 0.35,
        "open_interest": 0.25,
        "time_urgency": 0.20,
        "price_uncertainty": 0.20,
    }

    max_volume = max(m.volume_24h for m in markets) or 1
    max_oi = max(m.open_interest for m in markets) or 1

    scored = []
    for market in markets:
        vol_norm = market.volume_24h / max_volume
        oi_norm = market.open_interest / max_oi
        time_score = _time_urgency(market.days_remaining())
        uncertainty = _price_uncertainty(market.yes_price)

        hot_score = (
            w["volume"] * vol_norm
            + w["open_interest"] * oi_norm
            + w["time_urgency"] * time_score
            + w["price_uncertainty"] * uncertainty
        )
        scored.append((hot_score, market))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [m for _, m in scored[:top_n]]


def _time_urgency(days: float) -> float:
    """1.0 if closing today; linear decay to 0 at 7 days."""
    if days <= 0:
        return 0.0
    return max(0.0, 1.0 - days / 7.0)


def _price_uncertainty(yes_price: float) -> float:
    """Peak 1.0 at 0.50; 0.0 at 0.0 or 1.0. Mirrors parabola: 4p(1-p)."""
    p = max(0.0, min(1.0, yes_price))
    return 4 * p * (1 - p)


# ---------------------------------------------------------------------------
# Stage 2: Composite score (after enrichment + Claude analysis)
# ---------------------------------------------------------------------------

def compute_score_breakdown(
    market: Market,
    data: MarketData,
    weights: Optional[dict[str, float]] = None,
) -> ScoreBreakdown:
    """Compute the multi-dimensional composite score for a recommendation."""
    w = weights or {
        "edge_score": 0.30,
        "sentiment_alignment": 0.20,
        "market_consensus": 0.20,
        "vegas_alignment": 0.15,
        "liquidity_score": 0.10,
        "time_sensitivity": 0.05,
    }

    estimated = data.estimated_probability
    if estimated is None:
        estimated = market.yes_price  # No Claude estimate available

    # Edge score: how far is our estimate from market price?
    # An edge of 0.20 (20%) = maximum score of 1.0
    raw_edge = abs(estimated - market.yes_price)
    edge_score = min(1.0, raw_edge / 0.20)

    # Sentiment alignment: does aggregate sentiment agree with the edge direction?
    sentiment_score = data.aggregate_sentiment()
    if sentiment_score is not None and raw_edge > 0:
        # If estimated > market_price (we favor YES), positive sentiment = alignment
        direction = 1 if estimated > market.yes_price else -1
        alignment = sentiment_score * direction  # ranges -1 to +1
        sentiment_alignment = max(0.0, min(1.0, (alignment + 1) / 2))
    else:
        sentiment_alignment = 0.5  # neutral

    # Market consensus: Polymarket agreement with estimated direction
    if data.polymarket_probability is not None:
        poly_direction = data.polymarket_probability - market.yes_price
        est_direction = estimated - market.yes_price
        # Agreement = both on same side
        market_consensus = 0.8 if poly_direction * est_direction > 0 else 0.2
    else:
        market_consensus = 0.5

    # Vegas alignment (sports only)
    if data.vegas_probability is not None:
        vegas_direction = data.vegas_probability - market.yes_price
        est_direction = estimated - market.yes_price
        vegas_alignment = 0.9 if vegas_direction * est_direction > 0 else 0.1
    else:
        vegas_alignment = 0.5  # neutral if not available

    # Liquidity: less liquid = more edge opportunity (inverted volume)
    # Normalize: 0 volume = score 1.0, max volume = score 0.0
    # Use a soft inverse: score = 1 / (1 + volume / 5000)
    liquidity_score = 1.0 / (1.0 + market.volume_24h / 5000.0)

    # Time sensitivity
    time_sensitivity = _time_urgency(market.days_remaining())

    composite = (
        w["edge_score"] * edge_score
        + w["sentiment_alignment"] * sentiment_alignment
        + w["market_consensus"] * market_consensus
        + w["vegas_alignment"] * vegas_alignment
        + w["liquidity_score"] * liquidity_score
        + w["time_sensitivity"] * time_sensitivity
    )

    return ScoreBreakdown(
        edge_score=edge_score,
        sentiment_alignment=sentiment_alignment,
        market_consensus=market_consensus,
        vegas_alignment=vegas_alignment,
        liquidity_score=liquidity_score,
        time_sensitivity=time_sensitivity,
        composite_score=composite,
    )


def select_top_recommendations(
    recommendations: list[Recommendation],
    top_n: int = 5,
) -> list[Recommendation]:
    """Sort recommendations by composite score and return top N."""
    return sorted(
        recommendations,
        key=lambda r: r.score_breakdown.composite_score,
        reverse=True,
    )[:top_n]
