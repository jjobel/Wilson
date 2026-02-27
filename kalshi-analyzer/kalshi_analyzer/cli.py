"""CLI entry point for kalshi-analyzer."""

from __future__ import annotations

import argparse
import logging
import sys


def _configure_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    # Suppress noisy third-party loggers
    for lib in ("httpx", "httpcore", "praw", "prawcore", "tweepy", "yfinance"):
        logging.getLogger(lib).setLevel(logging.ERROR)


def cmd_analyze(args: argparse.Namespace) -> None:
    """Run the full analysis pipeline and print top recommendations."""
    from kalshi_analyzer.scheduler.pipeline import run_analysis

    run_analysis(config_path=args.config, top_n=args.n)


def cmd_markets(args: argparse.Namespace) -> None:
    """List currently hot markets without running analysis."""
    from kalshi_analyzer.config.settings import load_config
    from kalshi_analyzer.display.renderer import render_hot_markets_table
    from kalshi_analyzer.scorer.ranker import rank_hot_markets
    from kalshi_analyzer.sources.kalshi_source import KalshiSource

    config = load_config(args.config)
    markets_cfg = config.get("markets", {})

    kalshi = KalshiSource(
        min_volume=markets_cfg.get("min_volume", 100),
        days_ahead=markets_cfg.get("days_ahead", 7),
    )
    all_markets = kalshi.fetch_hot_markets()
    top = rank_hot_markets(all_markets, top_n=args.limit)
    render_hot_markets_table(top)


def cmd_inspect(args: argparse.Namespace) -> None:
    """Deep dive on a specific market ticker."""
    from kalshi_analyzer.analyzer.engine import AnalysisEngine
    from kalshi_analyzer.config.settings import load_config
    from kalshi_analyzer.display.renderer import render_market_deep_dive
    from kalshi_analyzer.models import MarketData
    from kalshi_analyzer.scheduler.pipeline import _build_sources
    from kalshi_analyzer.sources.kalshi_source import KalshiSource

    config = load_config(args.config)
    markets_cfg = config.get("markets", {})
    sources_cfg = config.get("sources", {})

    kalshi = KalshiSource(
        min_volume=0,  # No volume filter for inspect
        days_ahead=30,  # Wider window for inspect
    )
    all_markets = kalshi.fetch_hot_markets()
    market = next((m for m in all_markets if m.ticker == args.ticker), None)

    if market is None:
        print(f"Market '{args.ticker}' not found or already closed.", file=sys.stderr)
        sys.exit(1)

    sources = _build_sources(sources_cfg, min_volume=0, days_ahead=30)
    data = MarketData(market=market)
    for source in sources:
        try:
            data = source.enrich(market, data)
        except Exception as exc:
            logging.getLogger(__name__).debug("Source failed: %s", exc)

    engine = AnalysisEngine(
        model=config.get("anthropic", {}).get("model", "claude-sonnet-4-6"),
        max_tokens=config.get("anthropic", {}).get("max_tokens", 2048),
    )
    rec = engine.analyze_market(data)
    render_market_deep_dive(data, rec)


def cmd_schedule(args: argparse.Namespace) -> None:
    """Start the daily analysis scheduler daemon."""
    from apscheduler.schedulers.blocking import BlockingScheduler

    from kalshi_analyzer.config.settings import load_config
    from kalshi_analyzer.display.renderer import console
    from kalshi_analyzer.scheduler.pipeline import run_analysis

    config = load_config(args.config)
    cron_expr = config.get("schedule", {}).get("cron", "0 8 * * *")

    # Parse cron: "minute hour day month day_of_week"
    parts = cron_expr.split()
    if len(parts) == 5:
        minute, hour = parts[0], parts[1]
    else:
        minute, hour = "0", "8"

    scheduler = BlockingScheduler()
    scheduler.add_job(
        run_analysis,
        "cron",
        hour=hour,
        minute=minute,
        kwargs={"config_path": args.config, "top_n": 5},
    )

    console.print(
        f"[green]Scheduler started — running daily at {hour}:{minute.zfill(2)} UTC[/green]"
    )
    console.print("[dim]Press Ctrl+C to stop.[/dim]")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        console.print("\n[yellow]Scheduler stopped.[/yellow]")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kalshi-analyzer",
        description="Kalshi prediction market bet analyzer",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug logging"
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # analyze
    p_analyze = sub.add_parser("analyze", help="Run full analysis and show top bets")
    p_analyze.add_argument("-c", "--config", default="config.yaml", metavar="PATH")
    p_analyze.add_argument("-n", type=int, default=5, help="Number of recommendations")
    p_analyze.set_defaults(func=cmd_analyze)

    # markets
    p_markets = sub.add_parser("markets", help="List hot markets (no analysis)")
    p_markets.add_argument("-c", "--config", default="config.yaml", metavar="PATH")
    p_markets.add_argument("--limit", type=int, default=20, help="Number of markets to show")
    p_markets.set_defaults(func=cmd_markets)

    # inspect
    p_inspect = sub.add_parser("inspect", help="Deep dive on a specific market")
    p_inspect.add_argument("ticker", help="Kalshi market ticker (e.g. FEDRATEMAR-25)")
    p_inspect.add_argument("-c", "--config", default="config.yaml", metavar="PATH")
    p_inspect.set_defaults(func=cmd_inspect)

    # schedule
    p_schedule = sub.add_parser("schedule", help="Start daily scheduler daemon")
    p_schedule.add_argument("-c", "--config", default="config.yaml", metavar="PATH")
    p_schedule.set_defaults(func=cmd_schedule)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    _configure_logging(verbose=args.verbose)
    args.func(args)


if __name__ == "__main__":
    main()
