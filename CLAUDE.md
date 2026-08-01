# Casino-Coherent Momentum Dashboard

A personal stock dashboard built around a "casino-coherent momentum"
investment thesis: track a curated universe of tickers across thematic
sectors, surface signals that a stock is setting up for a meaningful move,
and contextualize them against broader-market reality. Not a commercial
product — personal/small-team use.

> **Note on names.** The GitHub repo is `ticker-video-digest` and the
> installable package is still `ticker-digest` for historical reasons. The
> **product** is this dashboard (`casino_dashboard`). A repository
> reorganization is planned — see `docs/reorg-plan-v1.md`.

## Subsystems

The repo currently hosts several subsystems that grew over time:

- **`casino_dashboard`** (`src/casino_dashboard/`) — THE PRODUCT. The live
  Streamlit dashboard: data layer, SQLite repository, daily signals, and UI.
  Entrypoints are `app.py` and `pages/` at the repo root.
- **`ticker_digest`** (`src/ticker_digest/`) — two things today:
  - the original **YouTube digest** feature (`youtube_client`, `transcripts`,
    `analyzer`, `cache`, and the `ticker` CLI subcommand). Currently a
    placeholder; still on the roadmap.
  - shared **market/social data infra** (`market/`, `social_media/`) that the
    dashboard, the CLI, and the daily-refresh job all depend on. (The reorg
    plan proposes lifting these into a neutral shared layer.)
- **FinTwit ingestion** (`orchestration/`, `storage/`, `tweet_sources/`) — a
  standalone tweet-ingestion pipeline writing to `data/fintwit.db`, driven by
  its own GitHub Actions. The reorg plan proposes grouping these under a
  single `fintwit` namespace.
- **Research** (`probes/`, root `*_probe.py`, `fetch_options.py`) — one-off
  diagnostics and committed run outputs.

## Usage shapes
- Streamlit dashboard: `streamlit run app.py` (root page + `pages/`).
- Dashboard daily refresh: `python -m casino_dashboard.jobs.daily_refresh`
  (runs in GitHub Actions — see Daily refresh ops).
- Market Reality Score CLI: `python -m ticker_digest market --thesis`.
- YouTube digest CLI (placeholder): `python -m ticker_digest ticker RKLB`.
- FinTwit ingestion: `python -m storage` / `python -m tweet_sources`
  (see each package's `__main__`).

## Stack
- Python 3.11
- setuptools + `pyproject.toml` (`uv.lock` committed); uv for dependency mgmt
- streamlit — web UI
- pandas, yfinance — market data
- google-api-python-client — YouTube Data API v3 (ticker_digest)
- youtube-transcript-api — caption extraction (ticker_digest)
- anthropic SDK — Claude API calls (thesis, per-video extraction)
- pydantic v2 — structured LLM output schemas
- SQLite (stdlib sqlite3) — `data/snapshots.db` (dashboard),
  `data/fintwit.db` (FinTwit), plus transcript/metadata caching
- praw / tweepy — social scrapers
- pytest — tests

## File layout (current, pre-reorg)
```
src/casino_dashboard/   # live dashboard: data/ db/ jobs/ signals/ ui/ models.py universe.py
src/ticker_digest/      # YouTube digest + shared market/ + social_media/
orchestration/          # FinTwit: worker pool, rate limiter, reconciler, runner
storage/                # FinTwit: SQLite layer for tweets/handles
tweet_sources/          # FinTwit: provider adapters (getxapi, twitterapi)
app.py                  # Streamlit dashboard entrypoint (root)
pages/                  # Streamlit dashboard pages 00–06
config/                 # themes.yaml (canonical universe), etf_mapping, star_traders, ...
data/                   # snapshots.db + fintwit.db (version-controlled prod data)
scripts/                # operational + one-time migration scripts
probes/                 # committed research run outputs
docs/                   # specs, context, and the reorg plan
tests/                  # pytest suite (mirrors the packages above)
pyproject.toml
README.md
```

## Analysis approach (ticker_digest YouTube feature)
Two-pass LLM pipeline:
1. Per-video extraction (Claude Sonnet 4.6) — transcript in, VideoInsights
   pydantic model out. Includes catalysts, red_flags, upcoming_events,
   sentiment, each with timestamp_seconds for citations.
2. Cross-video synthesis (Claude Opus 4.7) — list of VideoInsights in,
   DigestReport out. Aggregates themes, ranks by source count, preserves
   citations.

Enable prompt caching on the system prompt + schema definitions since
they're reused across the per-video pass.

## Conventions
- Type hints on every function signature
- Pydantic models for every structured data boundary
- No secrets in code — read from environment variables only
  (ANTHROPIC_API_KEY, YOUTUBE_API_KEY)
- No network calls in unit tests — use fixtures or mocks
- Log at INFO level for user-visible progress, DEBUG for diagnostics

## Quality filters — YouTube digest (pre-transcription)
- Minimum video duration: 120 seconds
- Minimum channel subscriber count: 500
- Exclude videos where title is ALL CAPS or contains rocket/fire emoji spam
- Prefer videos published in the last 7 days, sorted by view count

## Disclaimers
The output is aggregated commentary from public sources (YouTube videos,
social media, market data). It is not investment advice. The UI and CLI
must surface this clearly.

## Daily refresh ops

- The dashboard's daily refresh runs in GitHub Actions on schedule
  (`daily_refresh.yml`: 2am / 9am / 1pm / 5pm ET windows), **NOT locally**.
- `data/snapshots.db` is the production database and is version-controlled.
- The Action commits `data/snapshots.db` back to `main` automatically after each run.
- Local runs of the refresh job are for testing only — **DO NOT commit
  `data/snapshots.db` or `data/fintwit.db` from a local sandbox run** (it will
  overwrite production data with incomplete/test results).

## v6 canonical-files policy
The following files are CANONICAL CONFIGURATION. Do not modify, regenerate,
or replace them without an explicit prompt instructing you to do so:
- config/themes.yaml — the 8-sector ticker universe
- STRATEGY.md — the casino-coherent investment thesis
If a session begins and these files do not match what a prompt assumes,
STOP and report the mismatch. Do not "fix" them by overwriting.
