"""NASA ADS paper source for astrophysics journals (MNRAS, ApJ, A&A, etc.)."""

from __future__ import annotations

import logging
import os
from datetime import datetime

import httpx

from wilson.models import Paper
from wilson.sources.base import PaperSource

logger = logging.getLogger(__name__)

ADS_API_URL = "https://api.adsabs.harvard.edu/v1/search/query"

# Journals covered via ADS
ADS_JOURNALS = [
    "MNRAS",   # Monthly Notices of the Royal Astronomical Society
    "ApJ",     # The Astrophysical Journal
    "A&A",     # Astronomy & Astrophysics
    "AJ",      # The Astronomical Journal
    "PhRvL",   # Physical Review Letters
    "PhRvD",   # Physical Review D
]


class AdsSource(PaperSource):
    """Fetches papers from NASA ADS (covers major astrophysics journals)."""

    def __init__(self) -> None:
        self._api_token = os.environ.get("ADS_API_TOKEN", "")

    @property
    def name(self) -> str:
        return "ads"

    def fetch_recent(self, since: datetime, categories: list[str]) -> list[Paper]:
        """Fetch recent papers from ADS.

        Args:
            since: Only return papers published after this date.
            categories: Not used directly — ADS queries by journal bibstem.

        Returns:
            List of Paper objects from ADS-indexed journals.
        """
        if not self._api_token:
            logger.warning("ADS_API_TOKEN not set — skipping ADS source")
            return []

        date_str = since.strftime("%Y-%m-%d")
        bibstem_query = " OR ".join(f'bibstem:"{j}"' for j in ADS_JOURNALS)
        query = f"({bibstem_query}) AND pubdate:[{date_str} TO *]"

        headers = {"Authorization": f"Bearer {self._api_token}"}
        params = {
            "q": query,
            "fl": "title,author,abstract,bibcode,doi,pubdate,pub,identifier",
            "rows": 50,
            "sort": "date desc",
        }

        logger.info("Querying ADS: %s", query)

        try:
            response = httpx.get(ADS_API_URL, headers=headers, params=params, timeout=30)
            response.raise_for_status()
        except httpx.HTTPError:
            logger.exception("Failed to fetch from ADS")
            return []

        data = response.json()
        docs = data.get("response", {}).get("docs", [])

        papers = []
        for doc in docs:
            title = doc.get("title", ["Untitled"])[0]
            authors = doc.get("author", [])
            abstract = doc.get("abstract", "")
            bibcode = doc.get("bibcode", "")
            doi_list = doc.get("doi", [])
            doi = doi_list[0] if doi_list else None

            paper = Paper(
                title=title,
                authors=authors,
                abstract=abstract,
                url=f"https://ui.adsabs.harvard.edu/abs/{bibcode}",
                source=self.name,
                published=since,  # ADS pubdate is imprecise; use fetch window
                categories=[doc.get("pub", "")],
                doi=doi,
            )
            papers.append(paper)

        logger.info("Fetched %d papers from ADS", len(papers))
        return papers
