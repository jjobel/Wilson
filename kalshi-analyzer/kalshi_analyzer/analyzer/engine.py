"""Claude-powered analysis engine — synthesizes all market data into recommendations."""

from __future__ import annotations

import logging
import re

import anthropic

from kalshi_analyzer.models import (
    Confidence,
    Market,
    MarketData,
    Recommendation,
    ScoreBreakdown,
)
from kalshi_analyzer.scorer.ranker import compute_score_breakdown

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a quantitative prediction market analyst specializing in Kalshi markets.
Your job is to analyze evidence from multiple sources and determine whether a market \
is mispriced — i.e., whether the market price differs materially from the true probability.

Guidelines:
- Be evidence-driven. Cite specific data points from the provided context.
- Be explicit about uncertainty. Use ranges, not point estimates.
- Identify the key question: what single event or data release will resolve this market?
- Compare Kalshi price to Polymarket, Vegas lines, and news/sentiment signals.
- Recommend YES if you estimate the true probability is materially ABOVE the current price.
- Recommend NO if you estimate the true probability is materially BELOW the current price.
- Express confidence as High (>10% edge), Medium (5-10% edge), or Low (<5% edge).

Output your analysis ONLY using the following XML tags — do not add any other text:

<estimated_probability>XX%</estimated_probability>
<position>YES or NO</position>
<confidence>High or Medium or Low</confidence>
<evidence>
• bullet 1 (specific data point supporting your position)
• bullet 2
• bullet 3
</evidence>
<risks>
• risk 1 (specific scenario that would flip the outcome)
</risks>
<analysis>2-3 sentence summary of the key reasoning</analysis>
"""


class AnalysisEngine:
    """Generates bet recommendations from enriched MarketData using Claude."""

    def __init__(self, model: str = "claude-sonnet-4-6", max_tokens: int = 2048) -> None:
        self._client = anthropic.Anthropic()
        self._model = model
        self._max_tokens = max_tokens

    def analyze_market(self, data: MarketData) -> Recommendation:
        """Run Claude analysis on a MarketData bag and return a Recommendation.

        Falls back to a low-confidence heuristic recommendation if the Claude
        call fails.
        """
        market = data.market
        prompt = self._build_prompt(data)

        try:
            logger.info("Analyzing market: %s", market.ticker)
            response = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            response_text = response.content[0].text
            return self._parse_response(market, data, response_text)
        except Exception:
            logger.exception("Claude analysis failed for %s — using fallback", market.ticker)
            return self._fallback_recommendation(market, data)

    # ------------------------------------------------------------------
    # Prompt builder
    # ------------------------------------------------------------------

    def _build_prompt(self, data: MarketData) -> str:
        market = data.market
        parts: list[str] = []

        # Market header
        parts.append(f"## Market: {market.title}")
        parts.append(f"**Ticker**: {market.ticker}")
        parts.append(f"**Category**: {market.category.value}")
        parts.append(f"**Closes in**: {market.days_remaining():.1f} days")
        parts.append(f"**Kalshi Price**: YES={market.yes_price:.1%}  NO={market.no_price:.1%}")
        parts.append(f"**Volume 24h**: {market.volume_24h:,}")
        parts.append(f"**Open Interest**: {market.open_interest:,}")
        parts.append("")

        # Cross-market comparison
        comparisons: list[str] = []
        if data.polymarket_probability is not None:
            comparisons.append(f"Polymarket YES: {data.polymarket_probability:.1%}")
        if data.vegas_probability is not None:
            comparisons.append(f"Vegas Implied YES: {data.vegas_probability:.1%}")
        if comparisons:
            parts.append("## Market Comparison")
            parts.extend(comparisons)
            parts.append("")

        # News articles
        if data.news_articles:
            parts.append("## Recent News")
            for article in data.news_articles[:6]:
                sentiment_label = _sentiment_label(article.sentiment_score)
                parts.append(
                    f"- [{article.source}] {article.title} "
                    f"({article.published.strftime('%b %d')}, {sentiment_label})"
                )
                if article.snippet:
                    parts.append(f"  *{article.snippet[:200]}*")
            parts.append("")

        # Social sentiment
        sentiment_lines: list[str] = []
        if data.reddit_sentiment is not None:
            label = _sentiment_label(data.reddit_sentiment)
            sentiment_lines.append(f"Reddit: {data.reddit_sentiment:+.2f} ({label})")
        if data.twitter_sentiment is not None:
            label = _sentiment_label(data.twitter_sentiment)
            sentiment_lines.append(f"X/Twitter: {data.twitter_sentiment:+.2f} ({label})")
        if sentiment_lines:
            parts.append("## Social Sentiment")
            parts.extend(sentiment_lines)
            parts.append("")

        # Financial context
        if data.yfinance_context:
            parts.append("## Financial Market Context")
            parts.append(data.yfinance_context)
            parts.append("")

        # Data sources used
        if data.data_sources_used:
            parts.append(f"*Data sources: {', '.join(set(data.data_sources_used))}*")
            parts.append("")

        parts.append("Analyze this market and provide your recommendation.")
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Response parser
    # ------------------------------------------------------------------

    def _parse_response(self, market: Market, data: MarketData, text: str) -> Recommendation:
        estimated_probability = _extract_float_tag(text, "estimated_probability")
        position = _extract_text_tag(text, "position", "YES").upper()
        if position not in ("YES", "NO"):
            position = "YES"
        confidence_str = _extract_text_tag(text, "confidence", "Low").capitalize()
        confidence = Confidence(confidence_str) if confidence_str in Confidence._value2member_map_ else Confidence.LOW

        evidence_raw = _extract_text_tag(text, "evidence", "")
        evidence_bullets = [
            b.strip().lstrip("•- ") for b in evidence_raw.split("\n") if b.strip().startswith("•")
        ]

        risks_raw = _extract_text_tag(text, "risks", "")
        risk_warnings = [
            r.strip().lstrip("•- ") for r in risks_raw.split("\n") if r.strip().startswith("•")
        ]

        analysis_text = _extract_text_tag(text, "analysis", "")

        if estimated_probability is None:
            estimated_probability = market.yes_price

        data.estimated_probability = estimated_probability
        edge = estimated_probability - market.yes_price

        score = compute_score_breakdown(market, data)

        return Recommendation(
            market=market,
            position=position,
            confidence=confidence,
            estimated_probability=estimated_probability,
            edge=edge,
            score_breakdown=score,
            evidence_bullets=evidence_bullets,
            risk_warnings=risk_warnings,
            analysis_text=analysis_text,
        )

    def _fallback_recommendation(self, market: Market, data: MarketData) -> Recommendation:
        """Heuristic fallback when Claude is unavailable."""
        estimated_probability = market.yes_price  # No better estimate available
        data.estimated_probability = estimated_probability
        score = compute_score_breakdown(market, data)
        return Recommendation(
            market=market,
            position="YES",
            confidence=Confidence.LOW,
            estimated_probability=estimated_probability,
            edge=0.0,
            score_breakdown=score,
            evidence_bullets=["Analysis unavailable — Claude API call failed"],
            risk_warnings=["Do not use this recommendation without Claude analysis"],
            analysis_text="Fallback: Claude analysis failed. No edge identified.",
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_text_tag(text: str, tag: str, default: str = "") -> str:
    match = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return default


def _extract_float_tag(text: str, tag: str) -> float | None:
    raw = _extract_text_tag(text, tag)
    if not raw:
        return None
    try:
        # Handle "63%" or "0.63"
        raw = raw.replace("%", "").strip()
        value = float(raw)
        return value / 100.0 if value > 1.0 else value
    except ValueError:
        return None


def _sentiment_label(score: float) -> str:
    if score >= 0.35:
        return "Bullish"
    if score >= 0.15:
        return "Slightly Positive"
    if score >= -0.15:
        return "Neutral"
    if score >= -0.35:
        return "Slightly Negative"
    return "Bearish"
