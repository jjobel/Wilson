"""Daily digest pipeline — orchestrates fetch, summarize, and notify."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from wilson.config.settings import load_config
from wilson.models import Paper
from wilson.notifier.base import Notifier
from wilson.notifier.console import ConsoleNotifier
from wilson.notifier.pushover_notifier import PushoverNotifier
from wilson.sources.ads_source import AdsSource
from wilson.sources.arxiv_source import ArxivSource
from wilson.summarizer.engine import SummarizerEngine
from wilson.textbooks.indexer import TextbookIndexer

logger = logging.getLogger(__name__)

NOTIFIER_BACKENDS: dict[str, type] = {
    "console": ConsoleNotifier,
    "pushover": PushoverNotifier,
}


def run_daily_digest(config_path: str = "config.yaml") -> None:
    """Execute the full daily digest pipeline.

    1. Load configuration
    2. Fetch papers from all sources (last 24 hours)
    3. Generate summary via Claude API
    4. Send notification
    """
    config = load_config(config_path)

    # Determine time window
    since = datetime.now() - timedelta(hours=24)

    # Gather all arXiv categories from configured fields
    all_categories = []
    fields_map: dict[str, list[str]] = {}
    for field_cfg in config.get("fields", []):
        cats = field_cfg.get("arxiv_categories", [])
        all_categories.extend(cats)
        fields_map[field_cfg["name"]] = cats

    # Fetch papers from all sources
    papers: list[Paper] = []

    arxiv_source = ArxivSource()
    papers.extend(arxiv_source.fetch_recent(since, all_categories))

    ads_source = AdsSource()
    papers.extend(ads_source.fetch_recent(since, all_categories))

    logger.info("Total papers fetched: %d", len(papers))

    # Generate digest
    summarizer = SummarizerEngine(
        model=config.get("anthropic", {}).get("model", "claude-sonnet-4-6"),
        max_tokens=config.get("anthropic", {}).get("max_tokens", 4096),
    )
    digest = summarizer.create_digest(papers, fields_map)
    title, body = digest.format_notification()

    # Send notification
    backend_name = config.get("notifier", {}).get("backend", "console")
    notifier_cls = NOTIFIER_BACKENDS.get(backend_name, ConsoleNotifier)
    notifier: Notifier = notifier_cls()
    notifier.send(title, body)

    logger.info("Daily digest complete.")
