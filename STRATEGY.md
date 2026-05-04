# Casino Dashboard — Strategy

## What It Is

A live equity-intelligence dashboard for 8 speculative/growth sectors ("the casino").
Every day it ingests price, volume, and news for ~55 tickers, stores them in SQLite,
and surfaces a ranked view of momentum, sentiment, and catalyst signals.

## Why It Exists

Retail investors tracking high-risk/high-reward themes (space, quantum, nuclear, AI)
drown in noise. The dashboard cuts through by aggregating structured signals from
yfinance and (later) earnings transcripts, SEC filings, and YouTube commentary.

## Architecture — Three-Phase Roadmap

### Week 1 — Data Layer (this week)
- SQLite store for daily OHLCV + news (no UI, no analysis)
- Universe defined in `config/themes.yaml` (8 sectors, ~55 tickers)
- `jobs/daily_refresh.py` — idempotent daily ingest job
- Full unit + integration test coverage

### Week 2 — Signal Layer
- Per-ticker momentum score: price vs. 30-day avg, volume spike detection
- News sentiment via Claude (same two-pass pattern as ticker-digest)
- SectorSnapshot aggregation: weighted sector momentum score

### Week 3 — Dashboard UI
- Streamlit app: sector heat-map, ticker drill-down, news feed
- Filters: speculative-only toggle, sector selector, date range
- Disclaimer banner (not investment advice)

## Sector Philosophy

| Sector | Stage | Why Speculative |
|---|---|---|
| Space & Launch | Early | Long runway to profitability, binary mission risk |
| Defense & Dual-Use | Growth | Steady but event-driven (contracts, geopolitics) |
| Nuclear & Energy | Early | Regulatory overhang, decade-long build timelines |
| AI Infrastructure | Growth | High valuations, rapid obsolescence risk |
| Biotech & Gene Editing | Early | Binary FDA outcomes, cash-burn heavy |
| Electric Vehicles | Growth | Margin compression, China competition |
| Quantum Computing | Early | Pre-revenue, 5–10 year commercial horizon |
| Robotics & Automation | Growth | Valuation-sensitive to rate environment |

## Data Freshness Contract

- OHLCV: daily close, stored once per (ticker, date), idempotent on re-run
- News: last 5 items per ticker at fetch time, stored with `fetched_at` timestamp
- History retained indefinitely; no TTL on price data

## Multi-Tag Design

Tickers can appear in multiple sectors (e.g. RKLB in Space + Defense).
`Universe.sectors_for(ticker)` returns all sector IDs for a ticker.
Sector scores are computed independently; a multi-tagged ticker contributes
to each sector it belongs to.
