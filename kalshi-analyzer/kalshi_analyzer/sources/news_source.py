"""News source — fetches articles from NewsAPI and GDELT, scores with VADER."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Any

import httpx

from kalshi_analyzer.models import Market, MarketData, NewsArticle
from kalshi_analyzer.sources.base import DataSource

logger = logging.getLogger(__name__)

NEWSAPI_URL = "https://newsapi.org/v2/everything"
GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"


def _vader_score(text: str) -> float:
    """Return VADER compound sentiment score (-1 to +1) for text."""
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        sia = SentimentIntensityAnalyzer()
        return sia.polarity_scores(text)["compound"]
    except Exception:
        return 0.0


class NewsSource(DataSource):
    """Fetches recent news articles for a market topic."""

    def __init__(self, max_articles: int = 10) -> None:
        self._api_key = os.environ.get("NEWS_API_KEY", "")
        self._max_articles = max_articles

    @property
    def name(self) -> str:
        return "News"

    def is_available(self) -> bool:
        return True  # GDELT is always free; NewsAPI is optional enrichment

    def enrich(self, market: Market, data: MarketData) -> MarketData:
        """Fetch news articles and compute VADER sentiment scores."""
        # Build search query from first 6 words of title
        query = " ".join(market.title.split()[:6])
        articles: list[NewsArticle] = []

        # Try NewsAPI first (if key is set)
        if self._api_key:
            articles.extend(self._fetch_newsapi(query))

        # Always try GDELT (free)
        if len(articles) < self._max_articles:
            articles.extend(self._fetch_gdelt(query))

        # Deduplicate by title
        seen_titles: set[str] = set()
        unique: list[NewsArticle] = []
        for article in articles:
            key = article.title[:60].lower()
            if key not in seen_titles:
                seen_titles.add(key)
                unique.append(article)

        data.news_articles = unique[: self._max_articles]

        if data.news_articles:
            avg_tone = sum(a.sentiment_score for a in data.news_articles) / len(
                data.news_articles
            )
            data.gdelt_tone = avg_tone * 10  # scale to GDELT-like -100/+100 range
            data.data_sources_used.append(self.name)

        return data

    def _fetch_newsapi(self, query: str) -> list[NewsArticle]:
        articles: list[NewsArticle] = []
        from_date = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
        try:
            with httpx.Client(timeout=15) as client:
                resp = client.get(
                    NEWSAPI_URL,
                    params={
                        "q": query,
                        "from": from_date,
                        "sortBy": "relevancy",
                        "pageSize": self._max_articles,
                        "apiKey": self._api_key,
                        "language": "en",
                    },
                )
                if resp.status_code != 200:
                    return articles
                for raw in resp.json().get("articles", []):
                    art = _parse_newsapi_article(raw)
                    if art:
                        articles.append(art)
        except Exception:
            logger.debug("NewsAPI fetch failed for %r", query, exc_info=True)
        return articles

    def _fetch_gdelt(self, query: str) -> list[NewsArticle]:
        articles: list[NewsArticle] = []
        try:
            with httpx.Client(timeout=15) as client:
                resp = client.get(
                    GDELT_URL,
                    params={
                        "query": query,
                        "mode": "artlist",
                        "maxrecords": self._max_articles,
                        "format": "json",
                        "timespan": "7d",
                        "sort": "relevance",
                    },
                )
                if resp.status_code != 200:
                    return articles
                body = resp.json()
                for raw in body.get("articles", []):
                    art = _parse_gdelt_article(raw)
                    if art:
                        articles.append(art)
        except Exception:
            logger.debug("GDELT fetch failed for %r", query, exc_info=True)
        return articles


def _parse_newsapi_article(raw: dict[str, Any]) -> NewsArticle | None:
    title = raw.get("title", "").strip()
    if not title or title == "[Removed]":
        return None
    source = raw.get("source", {}).get("name", "Unknown")
    snippet = raw.get("description") or raw.get("content") or ""
    url = raw.get("url", "")
    published_str = raw.get("publishedAt", "")
    try:
        published = datetime.fromisoformat(published_str.replace("Z", "+00:00")).replace(
            tzinfo=None
        )
    except Exception:
        published = datetime.utcnow()

    text_for_sentiment = f"{title}. {snippet}"
    return NewsArticle(
        title=title,
        source=source,
        published=published,
        url=url,
        snippet=snippet[:300],
        sentiment_score=_vader_score(text_for_sentiment),
    )


def _parse_gdelt_article(raw: dict[str, Any]) -> NewsArticle | None:
    title = raw.get("title", "").strip()
    if not title:
        return None
    source = raw.get("domain", "Unknown")
    url = raw.get("url", "")
    snippet = raw.get("seendate", "")  # GDELT doesn't provide snippet text
    published_str = raw.get("seendate", "")
    try:
        published = datetime.strptime(published_str, "%Y%m%dT%H%M%SZ")
    except Exception:
        published = datetime.utcnow()

    return NewsArticle(
        title=title,
        source=source,
        published=published,
        url=url,
        snippet="",
        sentiment_score=_vader_score(title),  # Score title only for GDELT
    )
