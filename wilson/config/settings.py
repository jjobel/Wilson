"""Load and validate Wilson configuration from YAML."""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "fields": [
        {
            "name": "Astrophysics / Cosmology",
            "arxiv_categories": ["astro-ph.CO", "astro-ph.GA", "astro-ph.HE", "astro-ph.SR"],
            "keywords": ["dark matter", "dark energy", "gravitational waves", "CMB"],
        },
        {
            "name": "Quantum Physics / QFT",
            "arxiv_categories": ["quant-ph", "hep-th"],
            "keywords": ["quantum entanglement", "quantum field theory", "quantum computing"],
        },
    ],
    "schedule": {
        "time": "08:00",
        "timezone": "America/New_York",
    },
    "notifier": {
        "backend": "console",
    },
    "anthropic": {
        "model": "claude-sonnet-4-6",
        "max_tokens": 4096,
    },
    "textbooks": {
        "directory": "./textbooks/",
        "vector_store": "./data/vectors/",
    },
}


def load_config(path: str = "config.yaml") -> dict:
    """Load configuration from a YAML file, falling back to defaults.

    Args:
        path: Path to the config YAML file.

    Returns:
        Merged configuration dictionary.
    """
    config = dict(DEFAULT_CONFIG)
    config_path = Path(path)

    if config_path.exists():
        logger.info("Loading config from %s", path)
        with open(config_path) as f:
            user_config = yaml.safe_load(f) or {}

        # Merge user config over defaults (shallow merge per top-level key)
        for key, value in user_config.items():
            config[key] = value
    else:
        logger.info("No config file found at %s — using defaults", path)

    return config
