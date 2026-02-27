"""Terminal chart builders using plotext."""

from __future__ import annotations

from typing import Optional

from kalshi_analyzer.models import MarketData


def build_sentiment_chart(data: MarketData) -> str:
    """Return a plotext horizontal bar chart of sentiment scores as a string."""
    sources: list[tuple[str, float]] = []

    if data.reddit_sentiment is not None:
        sources.append(("Reddit", data.reddit_sentiment))
    if data.twitter_sentiment is not None:
        sources.append(("X/Twitter", data.twitter_sentiment))
    if data.news_articles:
        avg = sum(a.sentiment_score for a in data.news_articles) / len(data.news_articles)
        sources.append(("News", avg))
    if data.gdelt_tone is not None:
        # Normalize GDELT tone from ~-100/+100 scale to -1/+1
        sources.append(("GDELT", max(-1.0, min(1.0, data.gdelt_tone / 10.0))))

    if not sources:
        return _render_sentiment_fallback()

    return _render_sentiment_bars(sources)


def build_price_comparison_chart(data: MarketData) -> str:
    """Return a bar chart comparing Kalshi, Polymarket, Vegas, and estimated prices."""
    market = data.market
    bars: list[tuple[str, float]] = [("Kalshi", market.yes_price)]

    if data.polymarket_probability is not None:
        bars.append(("Polymarket", data.polymarket_probability))
    if data.vegas_probability is not None:
        bars.append(("Vegas", data.vegas_probability))
    if data.estimated_probability is not None:
        bars.append(("Est (AI)", data.estimated_probability))

    if len(bars) <= 1:
        return f"  YES Price: {market.yes_price:.1%}"

    return _render_probability_bars(bars)


def _render_sentiment_bars(sources: list[tuple[str, float]]) -> str:
    """Render colored horizontal bars in plain unicode (no plotext dependency needed)."""
    lines: list[str] = []
    bar_width = 20
    for label, score in sources:
        filled = int(abs(score) * bar_width)
        empty = bar_width - filled
        bar = ("█" * filled) + ("░" * empty)
        direction = "+" if score >= 0 else "-"
        sentiment = _label(score)
        lines.append(f"  {label:<10} {bar}  {direction}{abs(score):.2f}  [{sentiment}]")
    return "\n".join(lines)


def _render_probability_bars(bars: list[tuple[str, float]]) -> str:
    """Render probability comparison bars."""
    lines: list[str] = []
    bar_width = 20
    for label, prob in bars:
        filled = int(prob * bar_width)
        empty = bar_width - filled
        bar = ("█" * filled) + ("░" * empty)
        lines.append(f"  {label:<12} {bar}  {prob:.1%}")
    return "\n".join(lines)


def _render_sentiment_fallback() -> str:
    return "  No sentiment data available."


def _label(score: float) -> str:
    if score >= 0.35:
        return "Bullish"
    if score >= 0.15:
        return "Slightly +"
    if score >= -0.15:
        return "Neutral"
    if score >= -0.35:
        return "Slightly -"
    return "Bearish"
