# `casino_dashboard/` — the product

Everything the dashboard does, except the screen layout itself (that's in
[`pages/`](../../pages/README.md)).

---

## Sub-folders, in the order data moves through them

```
data/       fetch numbers from the outside world
   ↓
db/         store them in data/snapshots.db
   ↓
signals/    calculate the derived numbers
   ↓
jobs/       the scheduled work that runs all of the above
   ↓
ui/         helpers the pages use to display the result
```

### `data/` — getting the numbers

One file per source, and each one's job is "call the outside world, return
clean Python objects".

| File | Fetches |
|---|---|
| `yfinance_client.py` | Prices and volume from Yahoo Finance |
| `yfinance_metadata.py` | Company name, market cap, next earnings date |
| `etf_flows_fetcher.py` | Theme-ETF flows (the money-flow signal) |
| `congress_trades_fetcher.py` | Politicians' disclosed trades |
| `congress_legislators_fetcher.py` | Which politician sits on which committee |
| `deal_log_loader.py` | Reads `config/deal_log.yaml` |
| `manual_notes_loader.py` | Reads `config/manual_notes.yaml` |
| `star_traders_loader.py` | Reads `config/star_traders.yaml` |
| `subreddit_map_loader.py` | Reads `config/ticker_subreddits.yaml` |
| `ticker_validation.py` | "Is this a real ticker?" — used by the Add Stocks page |
| `models.py` | The shapes the data comes back in |

### `db/` — storing them

| File | Does |
|---|---|
| `schema.py` | Creates the tables. Safe to re-run. |
| `repository/` | **Every** database read and write in the dashboard, one module per subject |

`repository/` is a package, not a file — one module per subject area:

| Module | Owns |
|---|---|
| `snapshots.py` | Daily OHLCV rows and their news items |
| `signals.py` | Computed numbers: returns, RSI, distance from high/low |
| `social.py` | Reddit mention counts and the posts behind them |
| `metadata.py` | Company facts and hand-written notes |
| `sectors.py` | ETF flows, the deal log, sector heat rollups |
| `congress.py` | Congressional members, committees, disclosed trades |
| `user_universe.py` | Tickers and themes added via the Add Stocks page |

`repository/__init__.py` re-exports all of them, so
`from casino_dashboard.db.repository import save_snapshot` works regardless of
which module a function lives in. Add a new query to the module that owns the
subject, then list it in `__all__`.

If you're writing SQL anywhere else, move it here instead. One package owning
the database is what keeps the rest of the code readable.

### `signals/` — the maths

| File | Does |
|---|---|
| `computers.py` | The formulas for one stock: returns, distance from high/low, RSI |
| `orchestrator.py` | Runs those formulas across every stock and saves the results |
| `sector_aggregator.py` | Rolls stock-level numbers up into theme-level "heat" |

Nothing here touches the network. Numbers in, numbers out — which is why it's
the easiest part of the codebase to test.

### `jobs/` — the scheduled work

| File | Run by |
|---|---|
| `daily_refresh.py` | **The main one.** `daily_refresh.yml`, 4× every weekday |
| `reddit_pull.py`, `reddit_refresh.py` | Called by the daily refresh |
| `reddit_smoke_test.py` | `reddit_smoke_test.yml`, manually — "is Reddit still reachable?" |
| `subreddit_discovery_run.py` | Finds which subreddits discuss a stock |
| `subreddit_match_run.py` | Matches subreddits to companies by name |
| `subreddit_catalog_run.py` | Sweeps the archive for finance subreddits |
| `subreddit_metrics.py` | Size and activity stats for named subreddits |

`daily_refresh.py` runs thirteen stages, each individually error-handled so one
dead source can't kill the run. The stage list is in
[docs/start-here/04-how-the-data-flows.md](../../docs/start-here/04-how-the-data-flows.md).

### `ui/` — display helpers

Formatting, colours, and the loaders the pages call. `loaders.py` is the one
you'll touch most: it's the bridge between the database and the screen.

`components/` holds reusable pieces — the stat tile, the sector heat table, the
TradingView chart embed.

### Top-level files

| File | Does |
|---|---|
| `universe.py` | Loads `config/themes.yaml` **and merges in stocks added through the Add Stocks page**. The single answer to "which stocks are we watching?" |
| `models.py` | Shared data shapes |

---

## Where to make a change

| Change | File |
|---|---|
| A new data source | new file in `data/`, then call it from `jobs/daily_refresh.py` |
| A new stored field | `db/schema.py` **and** `db/repository.py` |
| A new calculated number | `signals/computers.py` + `signals/orchestrator.py` |
| Theme-level scoring | `signals/sector_aggregator.py` |
| What the daily job does | `jobs/daily_refresh.py` |
| How something is formatted | `ui/formatters.py` or `ui/formatting.py` |

Add a test in [`tests/`](../../tests/README.md) for anything in `signals/` or
`db/` — those are pure logic and cheap to cover.
