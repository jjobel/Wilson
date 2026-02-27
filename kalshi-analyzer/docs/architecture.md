# Kalshi Analyzer — Architecture

## Overview

`kalshi-analyzer` is a CLI tool that identifies the best Kalshi prediction market bets settling within the next 7 days. It collects evidence from six data sources, runs Claude-powered analysis, and presents recommendations with a rich terminal display.

## Pipeline

```
Kalshi API
    │
    ▼
fetch_hot_markets()        ← all open markets closing within 7 days
    │
    ▼
rank_hot_markets()         ← Stage 1: volume + uncertainty + time score → top 20
    │
    ▼  (parallel enrichment for each candidate)
    ├── PolymarketSource   ← cross-market probability comparison (free)
    ├── NewsSource         ← GDELT + NewsAPI articles (VADER scored)
    ├── SentimentSource    ← Reddit posts + X/Twitter tweets (VADER scored)
    ├── OddsSource         ← Vegas / bookmaker implied odds (SPORTS only)
    └── FinancialSource    ← yfinance macro data (ECONOMICS only)
    │
    ▼
AnalysisEngine (Claude)    ← per-market prompt → XML-structured response
    │
    ▼
compute_score_breakdown()  ← Stage 2: edge + sentiment + consensus + Vegas
    │
    ▼
select_top_recommendations()  ← top 5 by composite score
    │
    ▼
ConsoleNotifier            ← Rich terminal: market cards + recommendations table
  (or DiscordNotifier)
```

## Module Reference

### `kalshi_analyzer/models.py`
Core data models:
- `Market` — Kalshi market (ticker, prices, volume, category, close time)
- `MarketData` — enriched aggregate (market + all source data)
- `Recommendation` — final recommendation (position, confidence, edge, evidence)
- `ScoreBreakdown` — per-dimension scores

### `kalshi_analyzer/sources/`
All sources implement `DataSource` ABC:
- `is_available()` — returns False when API keys are missing (source is silently skipped)
- `enrich(market, data) -> MarketData` — modifies data in-place, returns it

| Source | Category Filter | Auth |
|--------|----------------|------|
| `KalshiSource` | All | None (public) |
| `PolymarketSource` | All | None |
| `NewsSource` | All | `NEWS_API_KEY` optional |
| `SentimentSource` | All | `TWITTER_BEARER_TOKEN` optional |
| `OddsSource` | SPORTS | `ODDS_API_KEY` required |
| `FinancialSource` | ECONOMICS | None (yfinance) |

### `kalshi_analyzer/scorer/ranker.py`
Two-stage scoring:

**Stage 1 — Hot score** (Kalshi data only):
```
hot_score = 0.35×vol + 0.25×oi + 0.20×time_urgency + 0.20×price_uncertainty
```
Selects top 20 candidates before any external API calls.

**Stage 2 — Composite score** (after enrichment + Claude):
```
composite = 0.30×edge + 0.20×sentiment + 0.20×consensus + 0.15×vegas + 0.10×liquidity + 0.05×time
```

### `kalshi_analyzer/analyzer/engine.py`
Claude-powered analysis via `anthropic.Anthropic`. Builds a structured prompt with:
- Market prices and metadata
- Cross-market comparison (Polymarket, Vegas)
- News articles with VADER scores
- Reddit + Twitter sentiment aggregates
- Financial macro context (economics only)

Returns XML-tagged response, parsed into `Recommendation`.

### `kalshi_analyzer/display/`
Rich terminal output:
- `charts.py` — Unicode bar charts for sentiment and probability comparison
- `news_panel.py` — Split-screen two-column news panel
- `market_panel.py` — Full per-market analysis card
- `recommendations.py` — Top-N recommendations table with colored cells
- `renderer.py` — Orchestrates progress bars and all display components

### `kalshi_analyzer/config/settings.py`
YAML config loader with deep-merge defaults. See `config.example.yaml` for schema.

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `ANTHROPIC_API_KEY` | **Yes** | Claude API |
| `KALSHI_API_KEY_ID` + `KALSHI_PRIVATE_KEY` | No | Kalshi auth (public endpoints work without) |
| `NEWS_API_KEY` | No | NewsAPI (GDELT runs free without) |
| `ODDS_API_KEY` | No | The Odds API Vegas lines (sports only) |
| `TWITTER_BEARER_TOKEN` | No | X/Twitter sentiment |
| `DISCORD_WEBHOOK_URL` | No | Discord notifications |

## Market Category Detection

Categories are detected via keyword matching against the market title and tags:

| Category | Keywords |
|----------|----------|
| SPORTS | nfl, nba, mlb, super bowl, championship, ufc... |
| ECONOMICS | fed, fomc, gdp, cpi, inflation, interest rate... |
| POLITICS | election, senate, president, vote, congress... |
| ENTERTAINMENT | oscar, grammy, box office, streaming... |
| WEATHER | hurricane, temperature, snow, drought... |
| GENERAL | (fallback, no keyword matches) |

Category determines which enrichment sources activate (OddsSource → SPORTS only, FinancialSource → ECONOMICS only).
