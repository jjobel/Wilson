# Wilson — Physics Research Assistant

Wilson is a personal physics research assistant that monitors scientific journals, summarizes new findings using AI, and delivers daily digests to your phone.

## What Wilson Does

- **Monitors journals daily** — Fetches new papers from arXiv, NASA ADS (covering MNRAS, ApJ, A&A), Physical Review Letters, and Nature Physics
- **Summarizes with AI** — Uses Claude to generate concise daily digests grouped by field, highlighting key results and emerging trends
- **Pushes to your iPhone** — Sends daily notifications with summaries so you stay current without manual browsing
- **Answers questions** — Ask Wilson physics questions and get answers backed by textbook references and recent papers
- **Indexes your textbooks** — Provide PDFs of your textbooks for RAG-powered Q&A with specific citations

## Fields Tracked

- **Astrophysics / Cosmology** — dark matter, dark energy, gravitational waves, CMB, galaxies, stellar physics
- **Quantum Physics / QFT** — quantum mechanics, quantum field theory, quantum computing, entanglement

## Quick Start

```bash
# Clone and install
git clone <repo-url> && cd Wilson
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Configure
cp config.example.yaml config.yaml
# Edit config.yaml with your preferences
# Set ANTHROPIC_API_KEY env var

# Run a digest now
wilson digest

# Ask a question
wilson ask "What is the latest evidence for dark energy evolution?"

# Index a textbook
wilson ingest path/to/textbook.pdf --name "Griffiths QM"

# Start the daily scheduler
wilson schedule
```

## Configuration

Copy `config.example.yaml` to `config.yaml` and customize:

- **fields** — Physics fields and arXiv categories to monitor
- **schedule** — What time to send the daily digest
- **notifier** — Notification backend (`console`, `pushover`, `telegram`)
- **anthropic** — Claude model and token settings
- **textbooks** — Paths for PDF storage and vector index

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Claude API key from Anthropic |
| `ADS_API_TOKEN` | For ADS source | NASA ADS API token |
| `PUSHOVER_API_TOKEN` | For Pushover | Pushover application token |
| `PUSHOVER_USER_KEY` | For Pushover | Your Pushover user key |

## Project Structure

```
Wilson/
├── wilson/
│   ├── sources/        # Journal and preprint fetchers (arXiv, ADS)
│   ├── summarizer/     # Claude API integration for digests and Q&A
│   ├── notifier/       # Push notification backends (Pushover, console)
│   ├── textbooks/      # PDF ingestion and RAG retrieval
│   ├── scheduler/      # Daily pipeline orchestration
│   ├── config/         # YAML configuration loading
│   ├── cli.py          # Command-line interface
│   └── models.py       # Shared data models (Paper, Digest)
├── docs/
│   └── architecture.md # Detailed system architecture
├── tests/
├── config.example.yaml
├── pyproject.toml
└── CLAUDE.md
```
