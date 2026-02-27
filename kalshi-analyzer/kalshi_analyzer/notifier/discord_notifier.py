"""Discord webhook notifier — sends a text summary of top recommendations."""

from __future__ import annotations

import logging
import os

import httpx

from kalshi_analyzer.models import Confidence, MarketData, Recommendation

logger = logging.getLogger(__name__)

CONFIDENCE_EMOJI = {
    Confidence.HIGH: "🟢",
    Confidence.MEDIUM: "🟡",
    Confidence.LOW: "🔴",
}


class DiscordNotifier:
    """Posts a formatted analysis summary to a Discord channel via webhook."""

    def __init__(self) -> None:
        self._webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "")

    def send(
        self,
        recommendations: list[Recommendation],
        market_data_list: list[MarketData],
    ) -> None:
        if not self._webhook_url:
            logger.warning("DISCORD_WEBHOOK_URL not set — skipping Discord notification")
            return

        content = self._format_message(recommendations)
        try:
            with httpx.Client(timeout=15) as client:
                resp = client.post(
                    self._webhook_url,
                    json={"content": content, "username": "Kalshi Analyzer"},
                )
                resp.raise_for_status()
                logger.info("Discord notification sent (%d chars)", len(content))
        except Exception:
            logger.exception("Discord notification failed")

    def _format_message(self, recs: list[Recommendation]) -> str:
        lines: list[str] = ["**📊 Kalshi Top Bets This Week**\n"]

        for i, rec in enumerate(recs, start=1):
            emoji = CONFIDENCE_EMOJI.get(rec.confidence, "⚪")
            edge_str = f"+{rec.edge:.0%}" if rec.edge >= 0 else f"{rec.edge:.0%}"
            lines.append(
                f"**{i}. {rec.market.title}** (`{rec.market.ticker}`)\n"
                f"{emoji} **{rec.position}** | {rec.confidence.value} confidence | "
                f"Kalshi: {rec.market.yes_price:.0%} → Est: {rec.estimated_probability:.0%} "
                f"(Edge: {edge_str})\n"
            )
            for bullet in rec.evidence_bullets[:2]:
                lines.append(f"  • {bullet}")
            if rec.risk_warnings:
                lines.append(f"  ⚠ {rec.risk_warnings[0]}")
            lines.append("")

        # Discord message limit: 2000 chars
        message = "\n".join(lines)
        if len(message) > 1950:
            message = message[:1947] + "..."
        return message
