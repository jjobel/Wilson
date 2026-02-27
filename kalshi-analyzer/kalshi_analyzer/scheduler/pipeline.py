"""Full analysis pipeline orchestrator."""

from __future__ import annotations

import logging
from typing import Any

from kalshi_analyzer.analyzer.engine import AnalysisEngine
from kalshi_analyzer.config.settings import load_config
from kalshi_analyzer.display.renderer import analysis_progress, console
from kalshi_analyzer.models import Market, MarketData, Recommendation
from kalshi_analyzer.notifier.base import Notifier
from kalshi_analyzer.notifier.console import ConsoleNotifier
from kalshi_analyzer.notifier.discord_notifier import DiscordNotifier
from kalshi_analyzer.scorer.ranker import rank_hot_markets, select_top_recommendations
from kalshi_analyzer.sources.base import DataSource
from kalshi_analyzer.sources.financial_source import FinancialSource
from kalshi_analyzer.sources.kalshi_source import KalshiSource
from kalshi_analyzer.sources.news_source import NewsSource
from kalshi_analyzer.sources.odds_source import OddsSource
from kalshi_analyzer.sources.polymarket_source import PolymarketSource
from kalshi_analyzer.sources.sentiment_source import SentimentSource

logger = logging.getLogger(__name__)

NOTIFIER_BACKENDS: dict[str, type] = {
    "console": ConsoleNotifier,
    "discord": DiscordNotifier,
}


def run_analysis(config_path: str = "config.yaml", top_n: int = 5) -> list[Recommendation]:
    """Execute the full Kalshi analysis pipeline.

    1. Load configuration
    2. Fetch hot markets from Kalshi
    3. Rank and select top candidates
    4. Enrich each candidate with all available data sources
    5. Run Claude analysis on each enriched market
    6. Select top N recommendations
    7. Notify

    Returns:
        List of top Recommendation objects.
    """
    config = load_config(config_path)
    markets_cfg = config.get("markets", {})
    sources_cfg = config.get("sources", {})
    top_n = markets_cfg.get("top_recommendations", top_n)
    hot_n = markets_cfg.get("hot_candidates", 20)
    min_volume = markets_cfg.get("min_volume", 100)
    days_ahead = markets_cfg.get("days_ahead", 7)

    # Build enrichment sources
    enrichment_sources = _build_sources(sources_cfg, min_volume, days_ahead)

    kalshi = KalshiSource(min_volume=min_volume, days_ahead=days_ahead)
    engine = AnalysisEngine(
        model=config.get("anthropic", {}).get("model", "claude-sonnet-4-6"),
        max_tokens=config.get("anthropic", {}).get("max_tokens", 2048),
    )

    with analysis_progress() as progress:
        # Step 1: Fetch markets
        fetch_task = progress.add_task("Fetching Kalshi markets...", total=None)
        all_markets = kalshi.fetch_hot_markets()
        progress.update(fetch_task, description=f"Fetched {len(all_markets)} markets", total=1, completed=1)

        if not all_markets:
            console.print("[yellow]No hot markets found. Check your config or Kalshi API.[/yellow]")
            return []

        # Step 2: Rank and filter
        ranking_weights = config.get("ranking", {}).get("weights")
        candidates = rank_hot_markets(all_markets, top_n=hot_n, weights=ranking_weights)

        # Step 3: Enrich
        enrich_task = progress.add_task("Enriching candidates...", total=len(candidates))
        enriched: list[MarketData] = []
        for market in candidates:
            data = MarketData(market=market)
            for source in enrichment_sources:
                try:
                    data = source.enrich(market, data)
                except Exception:
                    logger.exception("Source %s failed for %s", source.name, market.ticker)
            enriched.append(data)
            progress.advance(enrich_task)

        # Step 4: Claude analysis
        analysis_task = progress.add_task("Running Claude analysis...", total=len(enriched))
        analysis_weights = config.get("analysis", {}).get("weights")
        recommendations: list[Recommendation] = []
        for data in enriched:
            try:
                rec = engine.analyze_market(data)
                # Override weights if configured
                if analysis_weights:
                    from kalshi_analyzer.scorer.ranker import compute_score_breakdown
                    rec.score_breakdown = compute_score_breakdown(data.market, data, analysis_weights)
                    rec.score_breakdown.composite_score = _apply_weights(rec.score_breakdown, analysis_weights)
                recommendations.append(rec)
            except Exception:
                logger.exception("Analysis failed for %s", data.market.ticker)
            progress.advance(analysis_task)

        # Step 5: Select top N
        top_recs = select_top_recommendations(recommendations, top_n=top_n)

    # Step 6: Notify
    backend_name = config.get("notifier", {}).get("backend", "console")
    notifier_cls = NOTIFIER_BACKENDS.get(backend_name, ConsoleNotifier)
    notifier: Notifier = notifier_cls()
    notifier.send(top_recs, enriched)

    return top_recs


def _build_sources(sources_cfg: dict[str, Any], min_volume: int, days_ahead: int) -> list[DataSource]:
    """Build the list of enrichment sources based on config, skipping unavailable ones."""
    sources: list[DataSource] = []

    if sources_cfg.get("polymarket", {}).get("enabled", True):
        s = PolymarketSource()
        if s.is_available():
            sources.append(s)

    if sources_cfg.get("news", {}).get("enabled", True):
        max_articles = sources_cfg.get("news", {}).get("max_articles", 10)
        s = NewsSource(max_articles=max_articles)
        if s.is_available():
            sources.append(s)

    if sources_cfg.get("sentiment", {}).get("enabled", True):
        scfg = sources_cfg.get("sentiment", {})
        s = SentimentSource(
            reddit_post_limit=scfg.get("reddit_post_limit", 25),
            twitter_tweet_limit=scfg.get("twitter_tweet_limit", 100),
            twitter_min_likes=scfg.get("twitter_min_likes", 10),
        )
        if s.is_available():
            sources.append(s)

    if sources_cfg.get("odds", {}).get("enabled", True):
        s = OddsSource()
        if s.is_available():
            sources.append(s)
        else:
            logger.debug("Odds API not available (ODDS_API_KEY not set)")

    if sources_cfg.get("financial", {}).get("enabled", True):
        s = FinancialSource()
        if s.is_available():
            sources.append(s)

    logger.info("Active enrichment sources: %s", [s.name for s in sources])
    return sources


def _apply_weights(score: "ScoreBreakdown", weights: dict[str, float]) -> float:  # type: ignore[name-defined]
    return (
        weights.get("edge_score", 0.30) * score.edge_score
        + weights.get("sentiment_alignment", 0.20) * score.sentiment_alignment
        + weights.get("market_consensus", 0.20) * score.market_consensus
        + weights.get("vegas_alignment", 0.15) * score.vegas_alignment
        + weights.get("liquidity_score", 0.10) * score.liquidity_score
        + weights.get("time_sensitivity", 0.05) * score.time_sensitivity
    )
