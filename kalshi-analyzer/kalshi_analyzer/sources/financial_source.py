"""Financial context source — yfinance macro data for economics markets."""

from __future__ import annotations

import logging

from kalshi_analyzer.models import Market, MarketCategory, MarketData
from kalshi_analyzer.sources.base import DataSource

logger = logging.getLogger(__name__)

# Key financial tickers relevant to economic prediction markets
ECONOMIC_TICKERS = {
    "S&P 500": "^GSPC",
    "10Y Treasury": "^TNX",
    "Fed Funds Futures": "ZQ=F",
    "US Dollar Index": "DX-Y.NYB",
    "VIX": "^VIX",
    "Gold": "GC=F",
    "WTI Oil": "CL=F",
}


class FinancialSource(DataSource):
    """Fetches macro financial context via yfinance for economics markets."""

    @property
    def name(self) -> str:
        return "Financial"

    def is_available(self) -> bool:
        try:
            import yfinance  # noqa: F401
            return True
        except ImportError:
            return False

    def enrich(self, market: Market, data: MarketData) -> MarketData:
        """Add financial market context for economics-category markets."""
        if market.category != MarketCategory.ECONOMICS:
            return data

        context_lines: list[str] = []

        try:
            import yfinance as yf

            for label, ticker in ECONOMIC_TICKERS.items():
                try:
                    hist = yf.Ticker(ticker).history(period="5d")
                    if hist.empty:
                        continue
                    latest = hist["Close"].iloc[-1]
                    prior = hist["Close"].iloc[0]
                    change_pct = (latest - prior) / prior * 100
                    direction = "▲" if change_pct >= 0 else "▼"
                    context_lines.append(
                        f"{label}: {latest:.2f} ({direction}{abs(change_pct):.1f}% 5d)"
                    )
                except Exception:
                    logger.debug("yfinance failed for ticker %s", ticker, exc_info=True)

        except Exception:
            logger.debug("Financial source error", exc_info=True)

        if context_lines:
            data.yfinance_context = "\n".join(context_lines)
            data.data_sources_used.append(self.name)

        return data
