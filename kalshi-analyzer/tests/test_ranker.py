"""Tests for the two-stage ranking algorithm."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from kalshi_analyzer.models import Market, MarketCategory, MarketData, ScoreBreakdown
from kalshi_analyzer.scorer.ranker import (
    _price_uncertainty,
    _time_urgency,
    compute_score_breakdown,
    rank_hot_markets,
    select_top_recommendations,
)


def _make_market(
    ticker: str = "TEST",
    yes_price: float = 0.50,
    volume: int = 1000,
    open_interest: int = 500,
    days_ahead: float = 3.0,
) -> Market:
    return Market(
        ticker=ticker,
        title=f"Market {ticker}",
        category=MarketCategory.GENERAL,
        yes_price=yes_price,
        no_price=1 - yes_price,
        volume_24h=volume,
        open_interest=open_interest,
        close_time=datetime.utcnow() + timedelta(days=days_ahead),
    )


class TestHotMarketRanking:
    def test_returns_at_most_top_n(self):
        markets = [_make_market(ticker=f"M{i}", volume=i * 100) for i in range(10)]
        result = rank_hot_markets(markets, top_n=5)
        assert len(result) <= 5

    def test_high_volume_preferred(self):
        low_vol = _make_market(ticker="LOW", volume=100)
        high_vol = _make_market(ticker="HIGH", volume=50000)
        result = rank_hot_markets([low_vol, high_vol], top_n=2)
        assert result[0].ticker == "HIGH"

    def test_uncertain_price_preferred_over_near_certain(self):
        certain = _make_market(ticker="CERTAIN", yes_price=0.95, volume=1000)
        uncertain = _make_market(ticker="UNCERTAIN", yes_price=0.50, volume=1000)
        result = rank_hot_markets([certain, uncertain], top_n=2)
        assert result[0].ticker == "UNCERTAIN"

    def test_empty_list_returns_empty(self):
        assert rank_hot_markets([], top_n=5) == []

    def test_fewer_markets_than_top_n(self):
        markets = [_make_market(ticker=f"M{i}") for i in range(3)]
        result = rank_hot_markets(markets, top_n=10)
        assert len(result) == 3


class TestPriceUncertainty:
    def test_fifty_fifty_is_max(self):
        assert _price_uncertainty(0.50) == pytest.approx(1.0)

    def test_certain_yes_is_zero(self):
        assert _price_uncertainty(1.0) == pytest.approx(0.0)

    def test_certain_no_is_zero(self):
        assert _price_uncertainty(0.0) == pytest.approx(0.0)

    def test_symmetric(self):
        assert _price_uncertainty(0.3) == pytest.approx(_price_uncertainty(0.7))


class TestTimeUrgency:
    def test_closing_today_is_max(self):
        assert _time_urgency(0.1) == pytest.approx(0.986, abs=0.01)

    def test_seven_days_is_zero(self):
        assert _time_urgency(7.0) == pytest.approx(0.0)

    def test_linear_decay(self):
        assert _time_urgency(3.5) == pytest.approx(0.5)

    def test_expired_is_zero(self):
        assert _time_urgency(-1.0) == 0.0


class TestScoreBreakdown:
    def _data_with_estimate(
        self,
        market: Market,
        estimated: float,
        reddit: float | None = None,
        polymarket: float | None = None,
    ) -> MarketData:
        return MarketData(
            market=market,
            reddit_sentiment=reddit,
            polymarket_probability=polymarket,
            estimated_probability=estimated,
        )

    def test_edge_score_capped_at_one(self):
        m = _make_market(yes_price=0.50)
        data = self._data_with_estimate(m, estimated=0.95)  # 45% edge >> 20% cap
        score = compute_score_breakdown(m, data)
        assert score.edge_score <= 1.0

    def test_zero_edge_means_zero_edge_score(self):
        m = _make_market(yes_price=0.60)
        data = self._data_with_estimate(m, estimated=0.60)  # exact match
        score = compute_score_breakdown(m, data)
        assert score.edge_score == pytest.approx(0.0)

    def test_liquidity_inversely_correlates_with_volume(self):
        m_low = _make_market(ticker="LOW", volume=100)
        m_high = _make_market(ticker="HIGH", volume=100000)
        data_low = self._data_with_estimate(m_low, estimated=0.60)
        data_high = self._data_with_estimate(m_high, estimated=0.60)
        score_low = compute_score_breakdown(m_low, data_low)
        score_high = compute_score_breakdown(m_high, data_high)
        assert score_low.liquidity_score > score_high.liquidity_score

    def test_composite_score_in_unit_range(self):
        m = _make_market(yes_price=0.50)
        data = self._data_with_estimate(m, estimated=0.70, reddit=0.4, polymarket=0.65)
        score = compute_score_breakdown(m, data)
        assert 0.0 <= score.composite_score <= 1.0
