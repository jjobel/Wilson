# kalshi-analyzer

A Kalshi prediction market bet analyzer that finds the hottest markets settling within the next 7 days, gathers multi-source evidence, and recommends the top 5 bets using Claude AI.

## What it does

1. **Discovers** Kalshi markets closing within 7 days, ranked by volume and activity
2. **Gathers evidence** from 6 data sources for each candidate:
   - Kalshi live prices and order books
   - Polymarket cross-market probability comparison
   - NewsAPI + GDELT articles (with VADER sentiment scoring)
   - Reddit posts (public, no auth required)
   - X/Twitter posts (optional, requires API key)
   - Las Vegas / bookmaker odds (sports markets, optional)
   - yfinance macro data (economics markets, free)
3. **Analyzes** each market using Claude — synthesizing all evidence into an estimated probability and edge calculation
4. **Displays** a rich terminal output with market analysis cards, split-screen news, sentiment charts, and a final top-5 recommendations table

## Example Output

```
━━━━━━━━━━━━━━━ FEDRATEMAR  Will the Fed cut rates in March? ━━━━━━━━━━━━━━━
  Category: ECONOMICS  │  Closes: 4.0d  │  YES: 63%  │  Vol 24h: 12,345

  ┌─ Probability Comparison ──┐  ┌─ Sentiment Overview ─────────────────────┐
  │  Kalshi       ████████░░  │  │  Reddit   ████████░░  +0.42  [Bullish]   │
  │  Polymarket   █████████░  │  │  News     ██████░░░░  +0.31  [Slight +]  │
  │  AI Est       █████████░  │  │  X/Twitter████░░░░░░  +0.18  [Neutral]   │
  └───────────────────────────┘  └──────────────────────────────────────────┘

  ┌─ News Outlets ────────────────────────────────────────────────────────────┐
  │  [Reuters] 📈 "Fed signals rate cut...  │  [AP] 📈 "Inflation cools..."  │
  │  Feb 20 2026                           │  Feb 21 2026                    │
  └───────────────────────────────────────────────────────────────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━ TOP BETS THIS WEEK ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  # │ Market                    │ Pos │ Conf   │ Kalshi │ Est  │ Edge  │ Score
  ──┼───────────────────────────┼─────┼────────┼────────┼──────┼───────┼──────────
  1 │ Will Fed cut rates...     │ YES │ ● High │   63%  │  71% │  +8%  │ ████████░░ 0.82
    │ • FOMC dot plot leans cut │     │        │        │      │       │
    │ • Reddit/Twitter bullish  │     │        │        │      │       │
    │ ⚠ CPI print Friday = risk │     │        │        │      │       │
```

## Installation

```bash
git clone <repo>
cd kalshi-analyzer
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp config.example.yaml config.yaml
```

## Required Setup

```bash
export ANTHROPIC_API_KEY="your-key"   # Required
```

## Optional APIs (enrich analysis)

```bash
export NEWS_API_KEY="..."             # NewsAPI — more news articles
export ODDS_API_KEY="..."             # The Odds API — Vegas lines for sports
export TWITTER_BEARER_TOKEN="..."     # X/Twitter sentiment
export DISCORD_WEBHOOK_URL="..."      # Discord notifications
```

Reddit sentiment works without any API key (public read-only).

## Usage

```bash
# Full analysis — top 5 recommendations
kalshi-analyzer analyze

# List hot markets without analysis
kalshi-analyzer markets

# Deep dive on a specific market
kalshi-analyzer inspect FEDRATEMAR-25

# Start daily scheduler daemon (default: 8am UTC)
kalshi-analyzer schedule

# Options
kalshi-analyzer analyze -n 10 -c my-config.yaml -v
```

## Configuration

Edit `config.yaml` (copy from `config.example.yaml`). Key settings:

```yaml
markets:
  days_ahead: 7           # Markets closing within N days
  hot_candidates: 20      # Top N to deeply analyze
  top_recommendations: 5  # Final bets to show

notifier:
  backend: console        # "console" or "discord"

schedule:
  cron: "0 8 * * *"       # Daily at 8am UTC
```

## Architecture

See [docs/architecture.md](docs/architecture.md) for the full pipeline design.

## Testing

```bash
pytest
```

## Analysis Dimensions

Each bet is scored on 6 dimensions:

| Dimension | Weight | Description |
|-----------|--------|-------------|
| **Edge** | 30% | `|AI estimate − Kalshi price|` — the core mispricing signal |
| **Sentiment** | 20% | Reddit + News + X/Twitter agree with your position |
| **Market consensus** | 20% | Polymarket aligns with your estimated direction |
| **Vegas alignment** | 15% | Bookmaker odds agree (sports markets only) |
| **Liquidity** | 10% | Low-volume markets have more edge opportunity |
| **Time** | 5% | Markets closing sooner score higher |

## License

MIT
