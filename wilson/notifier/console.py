"""Console notifier — prints to stdout. Useful for development and testing."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class ConsoleNotifier:
    """Prints notifications to the console."""

    def send(self, title: str, body: str, url: str | None = None) -> bool:
        """Print a notification to stdout."""
        print(f"\n{'=' * 60}")
        print(f"  {title}")
        print(f"{'=' * 60}")
        print(body)
        if url:
            print(f"\nLink: {url}")
        print(f"{'=' * 60}\n")
        return True
