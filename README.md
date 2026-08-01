# Casino-Coherent Momentum Dashboard

A personal Streamlit dashboard that tracks a curated universe of tickers
across thematic sectors, surfaces daily momentum/setup signals, and
contextualizes them against broader-market reality.

> Repo name (`ticker-video-digest`) and package name (`ticker-digest`) are
> historical; the product is this dashboard. See `docs/reorg-plan-v1.md` for
> the planned cleanup and `STRATEGY.md` for the investment thesis.

```
# Dashboard
streamlit run app.py
```

Signals are refreshed daily by GitHub Actions (`daily_refresh.yml`) and the
SQLite database (`data/snapshots.db`) is committed back to `main`. The
universe of sectors/tickers is defined in `config/themes.yaml`.

## Subsystems

- **Dashboard** (`src/casino_dashboard/`, `app.py`, `pages/`) — the product.
- **Broader Market Reality Check** — benchmarks equity prices against
  real-economy fundamentals (see below).
- **ticker_digest** (`src/ticker_digest/`) — the original YouTube-digest
  feature (placeholder) plus shared `market/` and `social_media/` data infra.
- **FinTwit ingestion** (`orchestration/`, `storage/`, `tweet_sources/`) — a
  standalone tweet-ingestion pipeline writing to `data/fintwit.db`.

## Broader Market Reality Check

A Streamlit page (`pages/03_Market_Reality_Check.py`) and CLI subcommand that
benchmarks current equity prices against real-economy fundamentals.

- **Reality Score**: composite z-score of 14 indicators split into a market &
  sentiment bucket (Buffett indicator, CAPE proxy, margin debt, put/call,
  Mag-7 concentration, RSP/SPY breadth, AAII) and a real-economy bucket
  (10Y-2Y, industrial production YoY, unemployment, jobless claims, core CPI
  YoY, real retail sales YoY, M2 YoY). Positive scores indicate the market is
  priced richer than the economy supports; negative scores indicate the market
  is discounting weakness.
- **Claude-generated thesis**: Sonnet 4.6 narrative + bull/bear cases + watch
  items + regime label, cached by snapshot hash so reloads are free.
- **VIX** is shown separately as context (excluded from the composite).

```
# CLI
python -m ticker_digest market --thesis
```

Set `FRED_API_KEY` (free at https://fred.stlouisfed.org/docs/api/api_key.html)
to enable the real-economy bucket. Without it the dashboard still loads with
yfinance-only indicators.

Not investment advice.
