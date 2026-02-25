# CLAUDE.md — Wilson Physics Research Assistant

## Project Overview

Wilson is a physics research assistant that monitors scientific journals (arXiv, NASA ADS, etc.), summarizes new papers using the Claude API, and delivers daily digests via push notifications. It also supports Q&A with textbook-backed references via RAG.

- **Repository**: Wilson (Wilson-Virtual-Assistant)
- **Default branch**: `master`
- **Language**: Python 3.12+
- **AI Backend**: Claude API (Anthropic)

## Repository Structure

```
Wilson/
├── wilson/
│   ├── sources/            # Journal fetchers (arXiv API, NASA ADS)
│   │   ├── base.py         # PaperSource abstract base class
│   │   ├── arxiv_source.py # arXiv API integration
│   │   └── ads_source.py   # NASA ADS API integration
│   ├── summarizer/
│   │   └── engine.py       # Claude-powered digest generation and Q&A
│   ├── notifier/
│   │   ├── base.py         # Notifier protocol
│   │   ├── console.py      # Console output (dev/testing)
│   │   └── pushover_notifier.py  # iOS push via Pushover
│   ├── textbooks/
│   │   └── indexer.py      # PDF ingestion and vector search (ChromaDB)
│   ├── scheduler/
│   │   └── daily.py        # Daily digest pipeline orchestration
│   ├── config/
│   │   └── settings.py     # YAML config loader with defaults
│   ├── cli.py              # CLI entry point (wilson command)
│   └── models.py           # Shared data models (Paper, Digest)
├── tests/
├── docs/
│   └── architecture.md     # Detailed system architecture
├── config.example.yaml     # Example configuration
├── pyproject.toml          # Python project config and dependencies
├── .gitignore
├── CLAUDE.md               # This file
└── README.md
```

## Development Workflow

### Git Conventions

- **Default branch**: `master`
- **Feature branches**: Use descriptive branch names prefixed with your context (e.g., `claude/feature-name-sessionId`)
- **Commit messages**: Write clear, concise commit messages that describe *why* the change was made, not just what changed. Do NOT append Claude Code session links to commit messages.
- **Push**: Always use `git push -u origin <branch-name>`

### Code Style

- **Language**: Python 3.12+
- **Linter/Formatter**: Ruff (configured in `pyproject.toml`)
- **Line length**: 100 characters
- **Naming**: snake_case for files, variables, functions; PascalCase for classes
- **Type hints**: Use throughout; `from __future__ import annotations` at top of each module

### Testing

- **Framework**: pytest
- **Run tests**: `pytest` (from project root)
- **Test directory**: `tests/`
- **Test file naming**: `test_<module>.py`

### Building and Running

```bash
# Install dependencies
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run commands
wilson digest          # Run daily digest now
wilson ask "question"  # Ask a physics question
wilson ingest file.pdf # Index a textbook PDF
wilson schedule        # Start the daily scheduler daemon
```

### Key Environment Variables

- `ANTHROPIC_API_KEY` — Required for Claude API
- `ADS_API_TOKEN` — Required for NASA ADS source
- `PUSHOVER_API_TOKEN` / `PUSHOVER_USER_KEY` — Required for Pushover notifications

## Architecture Notes

- **Sources** return standardized `Paper` objects (see `wilson/models.py`)
- **Notifiers** implement the `Notifier` protocol (see `wilson/notifier/base.py`)
- **Textbook RAG** uses ChromaDB for vector storage with `pymupdf` for PDF extraction
- **Config** is YAML-based with sensible defaults (see `wilson/config/settings.py`)
- See `docs/architecture.md` for the full system design

## Guidelines for AI Assistants

1. **Read before editing** — Always read a file before modifying it. Understand existing code and conventions before making changes.
2. **Minimal changes** — Only make changes that are directly requested or clearly necessary. Avoid over-engineering.
3. **No guessing** — If requirements are unclear, ask for clarification rather than making assumptions.
4. **Security first** — Never introduce vulnerabilities (injection, XSS, etc.). Never commit secrets or credentials.
5. **Keep this file updated** — When you add significant structure (new directories, frameworks, build tools, test setups), update the relevant sections of this file so future sessions have accurate context.
