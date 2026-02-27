"""Split-screen news outlet panel builder."""

from __future__ import annotations

from rich.columns import Columns
from rich.panel import Panel
from rich.text import Text

from kalshi_analyzer.models import NewsArticle


def build_news_panel(articles: list[NewsArticle]) -> Panel:
    """Build a split-screen Panel showing news articles side by side."""
    if not articles:
        return Panel(
            Text("No news data available.", style="dim"),
            title="[bold]News Outlets[/bold]",
            border_style="blue",
        )

    # Split into two columns
    left = articles[:2]
    right = articles[2:4]

    left_text = _format_articles(left)
    right_text = _format_articles(right)

    columns = Columns(
        [
            Panel(left_text, border_style="dim blue", padding=(0, 1)),
            Panel(right_text, border_style="dim blue", padding=(0, 1)),
        ],
        equal=True,
    )

    return Panel(columns, title="[bold]News Outlets[/bold]", border_style="blue")


def _format_articles(articles: list[NewsArticle]) -> Text:
    text = Text()
    for i, article in enumerate(articles):
        if i > 0:
            text.append("\n\n")

        # Source badge
        text.append(f"[{article.source}]", style="bold cyan")
        text.append("  ")

        # Sentiment emoji
        emoji = _sentiment_emoji(article.sentiment_score)
        text.append(emoji + " ")

        # Headline
        headline = article.title[:70] + ("…" if len(article.title) > 70 else "")
        text.append(headline + "\n", style="bold white")

        # Date
        text.append(article.published.strftime("%b %d, %Y"), style="dim")

        # Snippet
        if article.snippet:
            snippet = article.snippet[:120] + ("…" if len(article.snippet) > 120 else "")
            text.append("\n" + snippet, style="italic dim white")

    return text


def _sentiment_emoji(score: float) -> str:
    if score >= 0.15:
        return "📈"
    if score <= -0.15:
        return "📉"
    return "➡"
