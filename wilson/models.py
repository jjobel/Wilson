"""Data models shared across Wilson modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Paper:
    """A scientific paper fetched from any source."""

    title: str
    authors: list[str]
    abstract: str
    url: str
    source: str  # e.g. "arxiv", "ads", "nature"
    published: datetime
    categories: list[str] = field(default_factory=list)
    doi: str | None = None

    def short_authors(self, max_authors: int = 3) -> str:
        """Return author string, truncated with 'et al.' if needed."""
        if len(self.authors) <= max_authors:
            return ", ".join(self.authors)
        return ", ".join(self.authors[:max_authors]) + " et al."


@dataclass
class Digest:
    """A daily digest of summarized papers."""

    date: datetime
    field_summaries: dict[str, str]  # field name -> summary text
    highlights: list[str]  # top insights across all fields
    paper_count: int
    papers: list[Paper] = field(default_factory=list)

    def format_notification(self) -> tuple[str, str]:
        """Return (title, body) formatted for a push notification."""
        title = f"Wilson Physics Digest — {self.date.strftime('%b %d')}"

        lines = [f"{self.paper_count} new papers across your fields.\n"]

        for field_name, summary in self.field_summaries.items():
            lines.append(f"**{field_name}**")
            lines.append(summary)
            lines.append("")

        if self.highlights:
            lines.append("**Key Insights**")
            for highlight in self.highlights:
                lines.append(f"• {highlight}")

        body = "\n".join(lines)
        return title, body
