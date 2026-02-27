"""Final top-5 recommendations table with rich styling."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from kalshi_analyzer.models import Confidence, Recommendation

# Unicode block progress bar
_FILLED = "█"
_EMPTY = "░"
_BAR_WIDTH = 10


def render_recommendations(recs: list[Recommendation], console: Console) -> None:
    """Print the formatted top-N recommendations table."""
    console.print()
    console.print(Rule("[bold gold1]TOP BETS THIS WEEK[/bold gold1]", style="gold1"))
    console.print()

    table = _build_table(recs)
    console.print(table)
    console.print()
    console.print(
        "[dim]Edge = AI estimated probability − Kalshi price. "
        "Positive edge = YES may be underpriced.[/dim]"
    )
    console.print()


def _build_table(recs: list[Recommendation]) -> Table:
    table = Table(
        show_header=True,
        header_style="bold white on dark_blue",
        show_lines=True,
        border_style="gold1",
        expand=True,
    )

    table.add_column("#", style="bold", width=3, justify="center")
    table.add_column("Market / Ticker", no_wrap=False, min_width=30)
    table.add_column("Pos", width=5, justify="center")
    table.add_column("Conf", width=8)
    table.add_column("Kalshi", width=8, justify="right")
    table.add_column("Est", width=7, justify="right")
    table.add_column("Edge", width=8, justify="right")
    table.add_column("Score", width=18)

    for i, rec in enumerate(recs, start=1):
        table.add_row(
            str(i),
            _market_cell(rec),
            _position_cell(rec.position),
            _confidence_cell(rec.confidence),
            f"{rec.market.yes_price:.0%}",
            f"{rec.estimated_probability:.0%}",
            _edge_cell(rec.edge),
            _score_bar(rec.score_breakdown.composite_score),
        )

    return table


def _market_cell(rec: Recommendation) -> Text:
    t = Text()
    t.append(rec.market.title + "\n", style="bold white")
    t.append(rec.market.ticker + "\n", style="dim cyan")

    for bullet in rec.evidence_bullets[:3]:
        t.append(f"  • {bullet}\n", style="dim")

    for risk in rec.risk_warnings[:1]:
        t.append(f"  ⚠ {risk}\n", style="yellow dim")

    return t


def _position_cell(position: str) -> Text:
    color = "bold green" if position == "YES" else "bold red"
    return Text(position, style=color, justify="center")


def _confidence_cell(confidence: Confidence) -> Text:
    colors = {
        Confidence.HIGH: "bold green",
        Confidence.MEDIUM: "bold yellow",
        Confidence.LOW: "bold red",
    }
    color = colors.get(confidence, "white")
    t = Text()
    t.append("● ", style=color)
    t.append(confidence.value, style=color)
    return t


def _edge_cell(edge: float) -> Text:
    pct = f"{edge:+.1%}"
    color = "bold green" if edge >= 0 else "bold red"
    return Text(pct, style=color, justify="right")


def _score_bar(score: float) -> str:
    filled = int(score * _BAR_WIDTH)
    empty = _BAR_WIDTH - filled
    bar = _FILLED * filled + _EMPTY * empty
    return f"{bar} {score:.2f}"
