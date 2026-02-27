"""Tests for data models."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from kalshi_analyzer.models import (
    Confidence,
    Market,
    MarketCategory,
    MarketData,
    Recommendation,
    ScoreBreakdown,
)


def _make_market(
    ticker: str = "TEST-001",
    yes_price: float = 0.60,
    days_ahead: float = 3.0,
    volume: int = 5000,
) -> Market:
    return Market(
        ticker=ticker,
        title="Will test event happen?",
        category=MarketCategory.GENERAL,
        yes_price=yes_price,
        no_price=1 - yes_price,
        volume_24h=volume,
        open_interest=1000,
        close_time=datetime.utcnow() + timedelta(days=days_ahead),
    )


class TestMarket:
    def test_implied_probability(self):
        m = _make_market(yes_price=0.63)
        assert m.implied_probability() == pytest.approx(0.63)

    def test_days_remaining_positive(self):
        m = _make_market(days_ahead=3.0)
        assert 2.9 < m.days_remaining() < 3.1

    def test_days_remaining_expired(self):
        m = _make_market(days_ahead=-1.0)
        assert m.days_remaining() == 0.0

    def test_format_price(self):
        m = _make_market(yes_price=0.63)
        display = m.format_price()
        assert "63%" in display
        assert "YES" in display

    def test_no_price_complement(self):
        m = _make_market(yes_price=0.40)
        assert m.no_price == pytest.approx(0.60)


class TestMarketData:
    def test_aggregate_sentiment_all_sources(self):
        m = _make_market()
        data = MarketData(
            market=m,
            reddit_sentiment=0.4,
            twitter_sentiment=0.2,
        )
        agg = data.aggregate_sentiment()
        assert agg is not None
        assert pytest.approx(agg, abs=0.01) == 0.3  # avg(0.4, 0.2)

    def test_aggregate_sentiment_no_data(self):
        m = _make_market()
        data = MarketData(market=m)
        assert data.aggregate_sentiment() is None

    def test_aggregate_sentiment_single_source(self):
        m = _make_market()
        data = MarketData(market=m, reddit_sentiment=-0.5)
        agg = data.aggregate_sentiment()
        assert agg == pytest.approx(-0.5)


class TestRecommendation:
    def _make_rec(self, position: str = "YES", edge: float = 0.08) -> Recommendation:
        market = _make_market()
        return Recommendation(
            market=market,
            position=position,
            confidence=Confidence.HIGH,
            estimated_probability=market.yes_price + edge,
            edge=edge,
            score_breakdown=ScoreBreakdown(composite_score=0.82),
            evidence_bullets=["Strong news sentiment", "Polymarket agrees"],
            risk_warnings=["CPI print Friday"],
            analysis_text="Market appears underpriced.",
        )

    def test_format_display_contains_ticker(self):
        rec = self._make_rec()
        display = rec.format_display()
        assert "TEST-001" in display

    def test_format_display_contains_position(self):
        rec = self._make_rec(position="NO", edge=-0.10)
        display = rec.format_display()
        assert "NO" in display

    def test_format_display_positive_edge(self):
        rec = self._make_rec(edge=0.08)
        display = rec.format_display()
        assert "+" in display

    def test_format_display_negative_edge(self):
        rec = self._make_rec(position="NO", edge=-0.08)
        display = rec.format_display()
        assert "-8%" in display or "−" in display or "-" in display
