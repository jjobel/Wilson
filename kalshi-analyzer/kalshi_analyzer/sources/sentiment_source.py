"""Sentiment source — Reddit and X/Twitter, scored with VADER."""

from __future__ import annotations

import logging
import os
from typing import Optional

from kalshi_analyzer.models import Market, MarketCategory, MarketData
from kalshi_analyzer.sources.base import DataSource

logger = logging.getLogger(__name__)

# Category → subreddits mapping
CATEGORY_SUBREDDITS: dict[MarketCategory, list[str]] = {
    MarketCategory.SPORTS: ["sports", "nfl", "nba", "baseball", "hockey"],
    MarketCategory.ECONOMICS: ["economics", "wallstreetbets", "investing", "finance"],
    MarketCategory.POLITICS: ["politics", "news", "worldnews"],
    MarketCategory.ENTERTAINMENT: ["entertainment", "movies", "music", "television"],
    MarketCategory.WEATHER: ["weather", "news"],
    MarketCategory.GENERAL: ["news", "worldnews"],
}


def _vader_score(text: str) -> float:
    """Return VADER compound sentiment score (-1 to +1)."""
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        sia = SentimentIntensityAnalyzer()
        return sia.polarity_scores(text)["compound"]
    except Exception:
        return 0.0


class SentimentSource(DataSource):
    """Aggregates sentiment from Reddit and X/Twitter using VADER scoring."""

    def __init__(
        self,
        reddit_post_limit: int = 25,
        twitter_tweet_limit: int = 100,
        twitter_min_likes: int = 10,
    ) -> None:
        self._reddit_post_limit = reddit_post_limit
        self._twitter_tweet_limit = twitter_tweet_limit
        self._twitter_min_likes = twitter_min_likes
        self._twitter_bearer = os.environ.get("TWITTER_BEARER_TOKEN", "")

    @property
    def name(self) -> str:
        return "Sentiment"

    def is_available(self) -> bool:
        return True  # Reddit always available; Twitter is optional

    def enrich(self, market: Market, data: MarketData) -> MarketData:
        """Score Reddit and X/Twitter sentiment for the market topic."""
        query = " ".join(market.title.split()[:5])

        reddit_score = self._score_reddit(query, market.category)
        if reddit_score is not None:
            data.reddit_sentiment = reddit_score

        if self._twitter_bearer:
            twitter_score = self._score_twitter(query)
            if twitter_score is not None:
                data.twitter_sentiment = twitter_score

        if data.reddit_sentiment is not None or data.twitter_sentiment is not None:
            data.data_sources_used.append(self.name)

        return data

    def _score_reddit(self, query: str, category: MarketCategory) -> Optional[float]:
        """Search relevant subreddits and return average VADER compound score."""
        try:
            import praw

            reddit = praw.Reddit(
                client_id="kalshi_analyzer",
                client_secret="kalshi_analyzer",
                user_agent="kalshi-analyzer/0.1 (read-only research tool)",
            )

            subreddits = CATEGORY_SUBREDDITS.get(category, ["news"])[:3]
            scores: list[float] = []

            for sub_name in subreddits:
                try:
                    sub = reddit.subreddit(sub_name)
                    for post in sub.search(
                        query, limit=self._reddit_post_limit, sort="relevance", time_filter="week"
                    ):
                        text = f"{post.title}. {post.selftext[:200]}"
                        scores.append(_vader_score(text))
                        # Top-level comments
                        post.comments.replace_more(limit=0)
                        for comment in list(post.comments)[:5]:
                            scores.append(_vader_score(comment.body[:200]))
                except Exception:
                    logger.debug("Reddit search failed for r/%s", sub_name, exc_info=True)

            if not scores:
                return None
            return sum(scores) / len(scores)

        except Exception:
            logger.debug("Reddit sentiment failed for %r", query, exc_info=True)
            return None

    def _score_twitter(self, query: str) -> Optional[float]:
        """Search recent X/Twitter posts and return average VADER compound score."""
        if not self._twitter_bearer:
            return None
        try:
            import tweepy

            client = tweepy.Client(bearer_token=self._twitter_bearer, wait_on_rate_limit=False)
            response = client.search_recent_tweets(
                query=f"{query} -is:retweet lang:en",
                max_results=min(self._twitter_tweet_limit, 100),
                tweet_fields=["public_metrics", "text"],
            )

            if not response.data:
                return None

            scores: list[float] = []
            for tweet in response.data:
                metrics = tweet.public_metrics or {}
                likes = metrics.get("like_count", 0)
                if likes >= self._twitter_min_likes:
                    scores.append(_vader_score(tweet.text))

            if not scores:
                return None
            return sum(scores) / len(scores)

        except Exception:
            logger.debug("Twitter sentiment failed for %r", query, exc_info=True)
            return None
