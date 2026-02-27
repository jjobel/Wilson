"""Per-market analysis card with sentiment chart, news, and comparison row."""

from __future__ import annotations

from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from kalshi_analyzer.display.charts import build_price_comparison_chart, build_sentiment_chart
from kalshi_analyzer.display.news_panel import build_news_panel
from kalshi_analyzer.models import MarketData


def render_market_card(data: MarketData, console: Console) -> None:
    """Print a full analysis card for one market to the console."""
    market = data.market

    # Header rule
    console.print(
        Rule(
            f"[bold yellow]{market.ticker}[/bold yellow]  [white]{market.title}[/white]",
            style="yellow",
        )
    )

    # Meta row
    meta = Table.grid(padding=(0, 2))
    meta.add_row(
        _badge("Category", market.category.value.upper(), "cyan"),
        _badge("Closes", f"{market.days_remaining():.1f}d", "magenta"),
        _badge("YES", f"{market.yes_price:.0%}", "green"),
        _badge("NO", f"{market.no_price:.0%}", "red"),
        _badge("Vol 24h", f"{market.volume_24h:,}", "blue"),
    )
    console.print(meta)

    # Charts: price comparison | sentiment overview (side by side)
    sentiment_chart_str = build_sentiment_chart(data)
    price_chart_str = build_price_comparison_chart(data)

    chart_columns = Columns(
        [
            Panel(
                price_chart_str,
                title="[bold]Probability Comparison[/bold]",
                border_style="dim green",
                padding=(0, 1),
            ),
            Panel(
                sentiment_chart_str,
                title="[bold]Sentiment Overview[/bold]",
                border_style="dim magenta",
                padding=(0, 1),
            ),
        ],
        equal=True,
    )
    console.print(chart_columns)

    # Split-screen news
    console.print(build_news_panel(data.news_articles))

    # Market comparison row
    comparison = _build_comparison_row(data)
    if comparison:
        console.print(
            Panel(
                comparison,
                title="[bold]Market Comparison[/bold]",
                border_style="dim white",
                padding=(0, 1),
            )
        )

    console.print()


def _badge(label: str, value: str, color: str) -> Text:
    t = Text()
    t.append(f"{label}: ", style="dim")
    t.append(value, style=f"bold {color}")
    return t


def _build_comparison_row(data: MarketData) -> str:
    market = data.market
    parts = [f"Kalshi: [green]{market.yes_price:.0%}[/green]"]
    if data.polymarket_probability is not None:
        parts.append(f"Polymarket: [cyan]{data.polymarket_probability:.0%}[/cyan]")
    if data.vegas_probability is not None:
        parts.append(f"Vegas: [yellow]{data.vegas_probability:.0%}[/yellow]")
    if data.estimated_probability is not None:
        parts.append(f"AI Estimate: [bold white]{data.estimated_probability:.0%}[/bold white]")
    return "  │  ".join(parts)
