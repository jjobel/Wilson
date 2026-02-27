"""Load and validate Kalshi Analyzer configuration from YAML."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

DEFAULT_CONFIG: dict[str, Any] = {
    "markets": {
        "days_ahead": 7,          # Only consider markets closing within N days
        "hot_candidates": 20,     # Top N to enrich before scoring
        "top_recommendations": 5, # Final top N to display
        "min_volume": 100,        # Skip markets with volume below this
    },
    "sources": {
        "kalshi": {"enabled": True},
        "polymarket": {"enabled": True},
        "news": {"enabled": True, "max_articles": 10},
        "sentiment": {
            "enabled": True,
            "reddit_post_limit": 25,
            "twitter_tweet_limit": 100,
            "twitter_min_likes": 10,
        },
        "odds": {"enabled": True},
        "financial": {"enabled": True},
    },
    "ranking": {
        "weights": {
            "volume": 0.35,
            "open_interest": 0.25,
            "time_urgency": 0.20,
            "price_uncertainty": 0.20,
        },
    },
    "analysis": {
        "weights": {
            "edge_score": 0.30,
            "sentiment_alignment": 0.20,
            "market_consensus": 0.20,
            "vegas_alignment": 0.15,
            "liquidity_score": 0.10,
            "time_sensitivity": 0.05,
        },
    },
    "anthropic": {
        "model": "claude-sonnet-4-6",
        "max_tokens": 2048,
    },
    "notifier": {
        "backend": "console",  # "console" or "discord"
    },
    "schedule": {
        "cron": "0 8 * * *",   # Daily at 8am
    },
}


def load_config(config_path: str = "config.yaml") -> dict[str, Any]:
    """Load configuration, merging user YAML over defaults.

    Args:
        config_path: Path to the user's config.yaml. If the file does not
                     exist, the default config is returned as-is.

    Returns:
        Merged configuration dictionary.
    """
    config = _deep_copy(DEFAULT_CONFIG)

    path = Path(config_path)
    if not path.exists():
        logger.debug("No config file found at %s — using defaults", config_path)
        return config

    with path.open() as fh:
        user_config = yaml.safe_load(fh) or {}

    _deep_merge(config, user_config)
    logger.debug("Loaded config from %s", config_path)
    return config


def _deep_copy(d: dict) -> dict:
    import copy
    return copy.deepcopy(d)


def _deep_merge(base: dict, override: dict) -> None:
    """Recursively merge override into base in-place."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
