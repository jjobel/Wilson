"""Core summarization engine using the Claude API."""

from __future__ import annotations

import logging
from datetime import datetime

import anthropic

from wilson.models import Digest, Paper

logger = logging.getLogger(__name__)

DIGEST_SYSTEM_PROMPT = """\
You are Wilson, a physics research assistant specializing in astrophysics, \
cosmology, and quantum physics. Your role is to summarize scientific papers \
into concise, accurate digests for a physicist.

Guidelines:
- Be precise with physics terminology
- Highlight novel results, not just methods
- Note connections between papers when relevant
- Keep summaries concise but substantive (2-3 sentences per paper)
- Group papers by subfield
- End with 2-3 key insights or emerging trends from the day's papers
"""

QA_SYSTEM_PROMPT = """\
You are Wilson, a physics research assistant. Answer physics questions \
accurately, citing relevant papers and textbook references when provided.

Guidelines:
- Be precise and rigorous
- Show key equations when they aid understanding
- Cite specific textbook sections and paper references provided in context
- Distinguish established results from speculative or cutting-edge claims
- If uncertain, say so rather than guessing
"""


class SummarizerEngine:
    """Generates digests and answers questions using the Claude API."""

    def __init__(self, model: str = "claude-sonnet-4-6", max_tokens: int = 4096) -> None:
        self._client = anthropic.Anthropic()
        self._model = model
        self._max_tokens = max_tokens

    def create_digest(self, papers: list[Paper], fields: dict[str, list[str]]) -> Digest:
        """Summarize a list of papers into a daily digest.

        Args:
            papers: Papers to summarize.
            fields: Mapping of field name to list of categories belonging to that field.

        Returns:
            A Digest object with per-field summaries and highlights.
        """
        if not papers:
            return Digest(
                date=datetime.now(),
                field_summaries={},
                highlights=["No new papers today."],
                paper_count=0,
            )

        # Group papers by field
        grouped: dict[str, list[Paper]] = {name: [] for name in fields}
        for paper in papers:
            for field_name, field_cats in fields.items():
                if any(cat in paper.categories for cat in field_cats):
                    grouped[field_name].append(paper)

        # Build prompt with paper details
        prompt_parts = ["Summarize today's physics papers:\n"]
        for field_name, field_papers in grouped.items():
            if not field_papers:
                continue
            prompt_parts.append(f"\n## {field_name} ({len(field_papers)} papers)\n")
            for p in field_papers:
                prompt_parts.append(
                    f"**{p.title}** — {p.short_authors()}\n"
                    f"Categories: {', '.join(p.categories)}\n"
                    f"Abstract: {p.abstract}\n"
                )

        prompt_parts.append(
            "\nProvide:\n"
            "1. A concise summary for each field (covering the key papers)\n"
            "2. 2-3 highlight insights or trends across all fields today"
        )

        prompt = "\n".join(prompt_parts)

        logger.info("Generating digest for %d papers", len(papers))
        response = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=DIGEST_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = response.content[0].text

        # Parse response into field summaries and highlights
        # For now, return the full response as a single digest
        # TODO: structured parsing of Claude's response into fields
        return Digest(
            date=datetime.now(),
            field_summaries={"All Fields": response_text},
            highlights=[],
            paper_count=len(papers),
            papers=papers,
        )

    def answer_question(
        self,
        question: str,
        textbook_context: str = "",
        paper_context: str = "",
    ) -> str:
        """Answer a physics question, optionally with textbook and paper context.

        Args:
            question: The user's physics question.
            textbook_context: Relevant textbook passages retrieved via RAG.
            paper_context: Relevant recent paper abstracts.

        Returns:
            The answer as a string.
        """
        prompt_parts = []

        if textbook_context:
            prompt_parts.append(
                f"**Relevant textbook references:**\n{textbook_context}\n"
            )
        if paper_context:
            prompt_parts.append(
                f"**Relevant recent papers:**\n{paper_context}\n"
            )

        prompt_parts.append(f"**Question:** {question}")
        prompt = "\n".join(prompt_parts)

        logger.info("Answering question: %s", question[:80])
        response = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=QA_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text
