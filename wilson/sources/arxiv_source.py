"""arXiv paper source using the arXiv API."""

from __future__ import annotations

import logging
from datetime import datetime

import arxiv

from wilson.models import Paper
from wilson.sources.base import PaperSource

logger = logging.getLogger(__name__)

# Mapping of Wilson field names to arXiv category prefixes
FIELD_CATEGORIES = {
    "astrophysics": ["astro-ph.CO", "astro-ph.GA", "astro-ph.HE", "astro-ph.SR", "astro-ph.IM"],
    "quantum": ["quant-ph", "hep-th"],
}


class ArxivSource(PaperSource):
    """Fetches papers from arXiv via their public API."""

    @property
    def name(self) -> str:
        return "arxiv"

    def fetch_recent(self, since: datetime, categories: list[str]) -> list[Paper]:
        """Fetch recent arXiv papers in the given categories.

        Args:
            since: Only return papers submitted after this time.
            categories: arXiv category strings (e.g. ["astro-ph.CO", "quant-ph"]).

        Returns:
            List of Paper objects from arXiv.
        """
        if not categories:
            logger.warning("No categories specified for arXiv fetch")
            return []

        # Build query: cat:astro-ph.CO OR cat:quant-ph OR ...
        cat_query = " OR ".join(f"cat:{cat}" for cat in categories)
        query = f"({cat_query})"

        logger.info("Querying arXiv: %s (since %s)", query, since.isoformat())

        client = arxiv.Client()
        search = arxiv.Search(
            query=query,
            max_results=100,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )

        papers = []
        for result in client.results(search):
            # Stop if we've gone past our time window
            if result.published.replace(tzinfo=None) < since:
                break

            paper = Paper(
                title=result.title,
                authors=[a.name for a in result.authors],
                abstract=result.summary,
                url=result.entry_id,
                source=self.name,
                published=result.published,
                categories=[c for c in result.categories if c in categories],
                doi=result.doi,
            )
            papers.append(paper)

        logger.info("Fetched %d papers from arXiv", len(papers))
        return papers
