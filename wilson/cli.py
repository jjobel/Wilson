"""Wilson CLI — entry point for running the assistant."""

from __future__ import annotations

import argparse
import logging
import sys


def main() -> None:
    """Main entry point for the Wilson CLI."""
    parser = argparse.ArgumentParser(
        prog="wilson",
        description="Wilson — Your physics research assistant",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    subparsers = parser.add_subparsers(dest="command")

    # `wilson digest` — run the daily digest pipeline
    digest_parser = subparsers.add_parser("digest", help="Run the daily digest pipeline now")
    digest_parser.add_argument(
        "-c", "--config",
        default="config.yaml",
        help="Path to config file (default: config.yaml)",
    )

    # `wilson ask` — ask a physics question
    ask_parser = subparsers.add_parser("ask", help="Ask Wilson a physics question")
    ask_parser.add_argument("question", nargs="+", help="Your physics question")
    ask_parser.add_argument(
        "-c", "--config",
        default="config.yaml",
        help="Path to config file (default: config.yaml)",
    )

    # `wilson ingest` — index a textbook PDF
    ingest_parser = subparsers.add_parser("ingest", help="Index a textbook PDF for reference")
    ingest_parser.add_argument("pdf_path", help="Path to the textbook PDF")
    ingest_parser.add_argument(
        "-n", "--name",
        help="Human-readable name for the textbook",
    )
    ingest_parser.add_argument(
        "-c", "--config",
        default="config.yaml",
        help="Path to config file (default: config.yaml)",
    )

    # `wilson schedule` — start the scheduler daemon
    schedule_parser = subparsers.add_parser("schedule", help="Start the daily digest scheduler")
    schedule_parser.add_argument(
        "-c", "--config",
        default="config.yaml",
        help="Path to config file (default: config.yaml)",
    )

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.command == "digest":
        from wilson.scheduler.daily import run_daily_digest
        run_daily_digest(args.config)

    elif args.command == "ask":
        from wilson.config.settings import load_config
        from wilson.summarizer.engine import SummarizerEngine
        from wilson.textbooks.indexer import TextbookIndexer

        config = load_config(args.config)
        question = " ".join(args.question)

        # Retrieve textbook context if available
        textbook_context = ""
        vector_store = config.get("textbooks", {}).get("vector_store", "./data/vectors/")
        try:
            indexer = TextbookIndexer(persist_dir=vector_store)
            textbook_context = indexer.query(question)
        except Exception:
            logging.debug("No textbook index available", exc_info=True)

        engine = SummarizerEngine(
            model=config.get("anthropic", {}).get("model", "claude-sonnet-4-6"),
            max_tokens=config.get("anthropic", {}).get("max_tokens", 4096),
        )
        answer = engine.answer_question(question, textbook_context=textbook_context)
        print(answer)

    elif args.command == "ingest":
        from wilson.config.settings import load_config
        from wilson.textbooks.indexer import TextbookIndexer

        config = load_config(args.config)
        vector_store = config.get("textbooks", {}).get("vector_store", "./data/vectors/")
        indexer = TextbookIndexer(persist_dir=vector_store)
        count = indexer.ingest_pdf(args.pdf_path, textbook_name=args.name)
        print(f"Indexed {count} chunks from {args.pdf_path}")

    elif args.command == "schedule":
        from apscheduler.schedulers.blocking import BlockingScheduler

        from wilson.config.settings import load_config
        from wilson.scheduler.daily import run_daily_digest

        config = load_config(args.config)
        schedule_cfg = config.get("schedule", {})
        time_str = schedule_cfg.get("time", "08:00")
        hour, minute = time_str.split(":")

        scheduler = BlockingScheduler()
        scheduler.add_job(
            run_daily_digest,
            "cron",
            hour=int(hour),
            minute=int(minute),
            args=[args.config],
        )
        print(f"Wilson scheduler started. Daily digest at {time_str}.")
        print("Press Ctrl+C to stop.")
        try:
            scheduler.start()
        except KeyboardInterrupt:
            print("\nScheduler stopped.")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
