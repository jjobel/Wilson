"""Rich terminal display orchestrator for the full analysis run."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table

from kalshi_analyzer.display.market_panel import render_market_card
from kalshi_analyzer.display.recommendations import render_recommendations
from kalshi_analyzer.models import Market, MarketData, Recommendation

# Shared console instance
console = Console()


@contextmanager
def analysis_progress() -> Generator[Progress, None, None]:
    """Context manager that returns a configured rich Progress bar."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
        transient=False,
    ) as progress:
        yield progress


def render_hot_markets_table(markets: list[Market]) -> None:
    """Print a compact table of hot markets (for `kalshi-analyzer markets` command)."""
    table = Table(
        title="[bold]Hot Kalshi Markets (Next 7 Days)[/bold]",
        show_header=True,
        header_style="bold cyan",
        border_style="blue",
        expand=True,
    )

    table.add_column("Ticker", style="bold yellow", no_wrap=True)
    table.add_column("Title", no_wrap=False)
    table.add_column("Category", justify="center")
    table.add_column("YES%", justify="right", style="green")
    table.add_column("Volume 24h", justify="right")
    table.add_column("Closes", justify="right")

    for m in markets:
        table.add_row(
            m.ticker,
            m.title[:60] + ("…" if len(m.title) > 60 else ""),
            m.category.value,
            f"{m.yes_price:.0%}",
            f"{m.volume_24h:,}",
            f"{m.days_remaining():.1f}d",
        )

    console.print(table)


def render_market_deep_dive(data: MarketData, rec: Recommendation | None = None) -> None:
    """Print a deep-dive card for a single market (for `inspect` command)."""
    render_market_card(data, console)
    if rec:
        render_recommendations([rec], console)


def render_full_analysis(
    market_data_list: list[MarketData],
    recommendations: list[Recommendation],
) -> None:
    """Print full analysis: per-market cards + recommendations table."""
    console.print()
    for data in market_data_list:
        render_market_card(data, console)

    render_recommendations(recommendations, console)
