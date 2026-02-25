# Wilson Architecture

## Overview

Wilson is a physics research assistant that monitors scientific journals, summarizes new findings, and answers physics questions with textbook-backed references. It delivers daily digests via push notifications.

## Target Physics Fields

- **Astrophysics / Cosmology** — stars, galaxies, dark matter/energy, CMB, gravitational waves
- **Quantum Physics / QFT** — quantum mechanics, quantum field theory, quantum computing, entanglement

## System Components

```
┌──────────────────────────────────────────────────────────┐
│                     Wilson Pipeline                       │
│                                                          │
│  ┌─────────────┐    ┌──────────────┐    ┌────────────┐  │
│  │   Sources    │───▶│  Summarizer  │───▶│  Notifier  │  │
│  │             │    │  (Claude API) │    │  (iPhone)  │  │
│  └─────────────┘    └──────┬───────┘    └────────────┘  │
│   • arxiv API              │                             │
│   • ADS / MNRAS            │                             │
│   • Phys Rev Letters       │                             │
│   • Nature Physics     ┌───▼────────┐                    │
│                        │ Textbook   │                    │
│                        │ Index (RAG)│                    │
│                        └────────────┘                    │
│                                                          │
│  ┌─────────────┐                                         │
│  │  Scheduler  │  Runs daily pipeline (once per day)     │
│  └─────────────┘                                         │
└──────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Sources (`wilson/sources/`)

Fetches new papers and articles from scientific journals.

| Source | Method | arXiv Categories |
|--------|--------|-----------------|
| **arXiv** | [arXiv API](https://info.arxiv.org/help/api/index.html) via `arxiv` Python package | `astro-ph.CO`, `astro-ph.GA`, `astro-ph.HE`, `astro-ph.SR`, `quant-ph`, `hep-th` |
| **NASA ADS** | [ADS API](https://ui.adsabs.harvard.edu/help/api/) | Covers MNRAS, ApJ, A&A, and other astrophysics journals |
| **Physical Review** | RSS feeds from APS journals | PRL, PRD, PRC |
| **Nature Physics** | RSS / web scraping | Nature Physics, Nature Astronomy |

Each source returns a standardized `Paper` object:

```python
@dataclass
class Paper:
    title: str
    authors: list[str]
    abstract: str
    url: str
    source: str           # e.g. "arxiv", "ads", "nature"
    published: datetime
    categories: list[str] # e.g. ["astro-ph.CO", "quant-ph"]
    doi: str | None
```

### 2. Summarizer (`wilson/summarizer/`)

Uses the **Claude API** (Anthropic) to:

- **Daily digest**: Summarize the day's papers into a concise briefing grouped by field
- **Trend detection**: Identify emerging themes across recent papers (weekly/monthly)
- **Q&A**: Answer physics questions, citing both papers and textbooks
- **Insight generation**: Highlight connections between papers across fields

The summarizer uses a system prompt tuned for physics expertise and concise scientific communication.

### 3. Notifier (`wilson/notifier/`)

Pluggable notification system with a common interface:

```python
class Notifier(Protocol):
    def send(self, title: str, body: str, url: str | None = None) -> bool: ...
```

Planned backends (user will choose):

| Backend | Cost | Setup Complexity | Notes |
|---------|------|-----------------|-------|
| **Pushover** | $5 one-time | Low | Purpose-built for programmatic notifications |
| **Email + Apple Shortcuts** | Free | Medium | Email triggers iOS Shortcut for notification |
| **Telegram Bot** | Free | Low | Requires Telegram app |
| **NTFY** | Free (self-host) | Medium | Open-source push notification service |

### 4. Textbook Index (`wilson/textbooks/`)

Retrieval-Augmented Generation (RAG) pipeline for user-provided textbooks:

1. **Ingest**: Accept PDF textbooks, extract text via `pymupdf` or `pdfplumber`
2. **Chunk**: Split text into semantically meaningful sections (by chapter/section headings)
3. **Embed**: Generate vector embeddings using a local model or API
4. **Store**: Persist embeddings in a local vector store (ChromaDB or similar)
5. **Retrieve**: When answering questions, retrieve relevant textbook passages and include as context for Claude

### 5. Scheduler (`wilson/scheduler/`)

Orchestrates the daily pipeline:

1. Fetch new papers from all sources (for the past 24 hours)
2. Filter by relevance to configured fields
3. Generate summaries via Claude API
4. Retrieve relevant textbook context if applicable
5. Format and send notification digest

Uses `APScheduler` or a simple cron-based approach. Configurable notification time (default: 8:00 AM local time).

### 6. Config (`wilson/config/`)

YAML-based configuration:

```yaml
# config.yaml
fields:
  - name: "Astrophysics / Cosmology"
    arxiv_categories: ["astro-ph.CO", "astro-ph.GA", "astro-ph.HE", "astro-ph.SR"]
    keywords: ["dark matter", "dark energy", "gravitational waves", "CMB"]
  - name: "Quantum Physics / QFT"
    arxiv_categories: ["quant-ph", "hep-th"]
    keywords: ["quantum entanglement", "quantum field theory", "quantum computing"]

schedule:
  time: "08:00"
  timezone: "America/New_York"

notifier:
  backend: "pushover"  # or "email", "telegram", "ntfy"
  # backend-specific settings loaded from environment variables

anthropic:
  model: "claude-sonnet-4-6"  # cost-effective for daily summaries
  max_tokens: 4096

textbooks:
  directory: "./textbooks/"
  vector_store: "./data/vectors/"
```

## Data Flow

```
Daily (scheduled):
  Sources ──▶ [Paper, Paper, ...] ──▶ Summarizer ──▶ Digest ──▶ Notifier ──▶ iPhone

On-demand (Q&A):
  User Question ──▶ Textbook Index (retrieve) ──▶ Summarizer (answer) ──▶ Response
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.12+ |
| AI Backend | Claude API (Anthropic) |
| arXiv Access | `arxiv` Python package |
| ADS Access | `ads` Python package / REST API |
| PDF Processing | `pymupdf` or `pdfplumber` |
| Vector Store | ChromaDB |
| Embeddings | `sentence-transformers` (local) or Voyage AI |
| Scheduling | APScheduler |
| Config | PyYAML |
| HTTP | `httpx` |
| Testing | `pytest` |
| Linting | `ruff` |
