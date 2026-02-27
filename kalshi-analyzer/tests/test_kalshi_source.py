"""Tests for KalshiSource — price parsing, category detection, HTTP errors."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from kalshi_analyzer.models import MarketCategory
from kalshi_analyzer.sources.kalshi_source import (
    KalshiSource,
    _detect_category,
    _parse_market,
)


def _raw_market(
    ticker: str = "TEST-001",
    yes_bid: int = 63,       # Kalshi returns cents (0-100)
    volume_24h: int = 5000,
    close_days: float = 3.0,
    title: str = "Will this happen?",
) -> dict:
    close_time = (datetime.utcnow() + timedelta(days=close_days)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    return {
        "ticker": ticker,
        "title": title,
        "yes_bid": yes_bid,
        "no_bid": 100 - yes_bid,
        "volume_24h": volume_24h,
        "open_interest": 1000,
        "close_time": close_time,
        "tags": [],
        "event_ticker": "EVENT-001",
        "subtitle": "",
        "last_price": yes_bid,
    }


class TestPriceConversion:
    def test_price_converted_from_cents(self):
        close_cutoff = datetime.utcnow() + timedelta(days=7)
        m = _parse_market(_raw_market(yes_bid=63), close_cutoff)
        assert m is not None
        assert m.yes_price == pytest.approx(0.63)

    def test_no_price_is_complement(self):
        close_cutoff = datetime.utcnow() + timedelta(days=7)
        m = _parse_market(_raw_market(yes_bid=63), close_cutoff)
        assert m is not None
        assert m.no_price == pytest.approx(0.37)

    def test_price_clamped_to_valid_range(self):
        close_cutoff = datetime.utcnow() + timedelta(days=7)
        raw = _raw_market(yes_bid=0)
        raw["yes_bid"] = 0
        m = _parse_market(raw, close_cutoff)
        assert m is not None
        assert m.yes_price >= 0.01

    def test_expired_market_returns_none(self):
        close_cutoff = datetime.utcnow() + timedelta(days=7)
        m = _parse_market(_raw_market(close_days=-1.0), close_cutoff)
        assert m is None

    def test_beyond_cutoff_returns_none(self):
        close_cutoff = datetime.utcnow() + timedelta(days=3)
        m = _parse_market(_raw_market(close_days=5.0), close_cutoff)
        assert m is None


class TestCategoryDetection:
    def test_detects_sports(self):
        cat = _detect_category("Will the NFL Super Bowl winner be the Chiefs?", [])
        assert cat == MarketCategory.SPORTS

    def test_detects_economics(self):
        cat = _detect_category("Will the Fed raise interest rates in March?", [])
        assert cat == MarketCategory.ECONOMICS

    def test_detects_politics(self):
        cat = _detect_category("Will Senate pass the new immigration bill?", [])
        assert cat == MarketCategory.POLITICS

    def test_falls_back_to_general(self):
        cat = _detect_category("Will a new category exist?", [])
        assert cat == MarketCategory.GENERAL

    def test_tags_contribute_to_detection(self):
        cat = _detect_category("Will it happen?", ["nba", "basketball"])
        assert cat == MarketCategory.SPORTS


class TestFetchHotMarkets:
    def test_http_error_returns_empty_list(self):
        source = KalshiSource()
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            import httpx
            mock_client.get.side_effect = httpx.HTTPError("Connection refused")
            result = source.fetch_hot_markets()
        assert result == []

    def test_volume_filter_applied(self):
        close_cutoff = datetime.utcnow() + timedelta(days=7)
        low_volume = _parse_market(_raw_market(volume_24h=50), close_cutoff)
        high_volume = _parse_market(_raw_market(volume_24h=5000), close_cutoff)
        # Low volume market parsed fine, but KalshiSource with min_volume=100 should skip it
        source = KalshiSource(min_volume=100)
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            response_mock = MagicMock()
            response_mock.status_code = 200
            response_mock.json.return_value = {
                "markets": [
                    _raw_market(ticker="LOW-VOL", volume_24h=50),
                    _raw_market(ticker="HIGH-VOL", volume_24h=5000),
                ],
                "cursor": None,
            }
            response_mock.raise_for_status = MagicMock()
            mock_client.get.return_value = response_mock
            result = source.fetch_hot_markets()

        tickers = [m.ticker for m in result]
        assert "HIGH-VOL" in tickers
        assert "LOW-VOL" not in tickers
