"""Rich-powered console notifier — prints analysis cards + recommendations table."""

from __future__ import annotations

import logging

from kalshi_analyzer.display.renderer import console, render_full_analysis
from kalshi_analyzer.models import MarketData, Recommendation

logger = logging.getLogger(__name__)


class ConsoleNotifier:
    """Renders the full analysis to stdout using the Rich display module."""

    def send(
        self,
        recommendations: list[Recommendation],
        market_data_list: list[MarketData],
    ) -> None:
        if not recommendations:
            console.print("[yellow]No recommendations generated.[/yellow]")
            return

        # Only display market cards for markets that made the final top-N
        top_tickers = {r.market.ticker for r in recommendations}
        filtered_data = [d for d in market_data_list if d.market.ticker in top_tickers]

        render_full_analysis(filtered_data, recommendations)
        logger.info("Console output complete — %d recommendations displayed", len(recommendations))
