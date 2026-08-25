# Casino-Coherent Momentum Dashboard

A personal stock dashboard built around a "casino-coherent momentum"
investment thesis: track a curated universe of tickers across thematic
sectors, surface signals that a stock is setting up for a meaningful move,
and contextualize them against broader-market reality. Not a commercial
product — personal/small-team use.

> **Note on names.** The GitHub repo is `ticker-video-digest` and the
> installable package is still `ticker-digest` for historical reasons. The
> **product** is this dashboard (`casino_dashboard`). The repository was
> reorganized into the layout below — see `docs/archive/reorg-plan-v1.md` for the
> rationale and history.

## Where the documentation lives

Read `docs/README.md` first — it indexes everything. The structure is:

- `docs/start-here/` — the onboarding path (7 numbered pages, written for a
  non-technical reader). **Keep these accurate**: they are the first thing a
  new person reads, and stale onboarding is worse than none.
- `docs/runbooks/` — how to operate a live subsystem
- `docs/specs/` — design decisions, written before the code
- `docs/research/` — findings from investigations
- `docs/archive/` — point-in-time snapshots; assume stale
- Every major folder also has its own `README.md` (`src/`, each package,
  `config/`, `data/`, `pages/`, `scripts/`, `tests/`, `research/`,
  `.github/workflows/`). When you change what a folder contains, update it.

`./run` at the repo root wraps the common commands (`setup`, `dashboard`,
`test`, `check`, `market`, `digest`, `threads`, `refresh`, `clean`). Prefer
teaching it over raw commands in user-facing docs.

## Subsystems

All importable code lives under `src/` in four packages:

- **`casino_dashboard`** (`src/casino_dashboard/`) — THE PRODUCT. The live
  Streamlit dashboard: data layer, SQLite repository, daily signals, and UI.
  Entrypoints are `app.py` and `pages/` at the repo root.
- **`core`** (`src/core/`) — shared substrate imported by both the dashboard
  and the YouTube feature: `models`, `config`, `cache`, and the `market/` +
  `social_media/` data sources.
- **`ticker_digest`** (`src/ticker_digest/`) — the **YouTube insight threads**
  feature (`sources`, `quality`, `youtube_client`, `transcripts`, `analyzer`,
  `novelty`, `thread`, `store`, `pipeline`, and the `ticker`/`threads` CLI
  subcommands), importing shared bits from `core`. Runs end to end from the
  CLI; stores runs, claims and threads in `data/digests.db`. Not scheduled and
  not on the dashboard yet — see `docs/specs/youtube-insight-threads-v1.md`.
- **`fintwit`** (`src/fintwit/`) — a standalone tweet-ingestion pipeline
  (`orchestration/`, `storage/`, `tweet_sources/`) writing to
  `data/fintwit.db`, driven by its own GitHub Actions.

Non-package trees: **`research/`** (one-off probes + committed run outputs),
**`scripts/`** (operational + migration scripts), **`config/`**, **`data/`**.

## Usage shapes
- Streamlit dashboard: `streamlit run app.py` (root page + `pages/`).
- Dashboard daily refresh: `python -m casino_dashboard.jobs.daily_refresh`
  (runs in GitHub Actions — see Daily refresh ops).
- Market Reality Score CLI: `python -m ticker_digest market --thesis`.
- YouTube insight thread: `python -m ticker_digest ticker RKLB`
  (add `--channel @handle` to read one trusted channel instead of searching).
- Stored threads: `python -m ticker_digest threads --ticker RKLB`.
- FinTwit ingestion: `python -m fintwit.storage` / `python -m fintwit.tweet_sources`
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
  `data/fintwit.db` (FinTwit), `data/digests.db` (YouTube threads,
  git-ignored), plus transcript/metadata caching
- praw / tweepy — social scrapers
- pytest — tests

## File layout
```
src/casino_dashboard/   # live dashboard: data/ db/ jobs/ signals/ ui/ models.py universe.py
src/core/               # shared: models.py config.py cache.py market/ social_media/
src/ticker_digest/      # YouTube insight threads: sources quality novelty thread store pipeline cli
src/fintwit/            # tweet ingestion: orchestration/ storage/ tweet_sources/
app.py                  # Streamlit dashboard entrypoint (root)
pages/                  # Streamlit dashboard pages 00–06
config/                 # themes.yaml (canonical universe), etf_mapping, star_traders, ...
data/                   # snapshots.db + fintwit.db (version-controlled prod data)
scripts/                # operational + one-time migration scripts
research/               # one-off probes + committed run outputs
docs/                   # start-here/ runbooks/ specs/ research/ archive/
tests/                  # pytest suite (mirrors the packages above)
run                     # task runner: ./run setup|dashboard|test|check|market|digest|threads|refresh|clean
.env.example            # every supported env var, documented
pyproject.toml
README.md
```

Every major folder carries a `README.md` explaining itself — treat those as
part of the code and keep them in sync with what the folder actually holds.

## Analysis approach (ticker_digest YouTube feature)
Two-pass LLM pipeline, with a novelty check between the passes:
1. Per-video extraction (Claude Sonnet 4.6) — transcript in, VideoInsights
   pydantic model out. Includes catalysts, red_flags, upcoming_events,
   sentiment, each with timestamp_seconds for citations.
2. Novelty — extracted claims are compared against claims stored from earlier
   runs for that ticker: deterministic fingerprint/similarity match first, then
   Claude for whatever survives. Each claim ends up new / developing / known.
   A claim holds every citation that supports it, so "four of five videos said
   this" survives; a known claim repeated by a channel that never said it
   before is flagged newly_corroborated.
3. Cross-video synthesis (Claude Opus 4.7) — judged claims in, InsightThread
   out: an ordered thread of posts led by what's new, citations preserved.

Enable prompt caching on the system prompt + schema definitions since
they're reused across the per-video pass.

The delta is the product: a run where nothing is new must say so rather than
restate the standing bull case. Ranking and duplicate detection stay
deterministic and unit-tested (`quality.py`, `novelty.partition`); the LLM is
reserved for judgement the code can't do.

## Conventions
- Type hints on every function signature
- Pydantic models for every structured data boundary
- No secrets in code — read from environment variables only. Every supported
  variable is documented in `.env.example`; add new ones there too.
- No network calls in unit tests — use fixtures or mocks
- Log at INFO level for user-visible progress, DEBUG for diagnostics
- Docs: a new document goes in the right `docs/` subfolder **and** gets a row
  in `docs/README.md`. A doc nobody can find isn't documentation.
- Write `docs/start-here/` for a non-technical reader: no unexplained jargon,
  copy-pasteable commands, and say what the expected output looks like.

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
- config/themes.yaml — the thematic ticker universe (currently 12 sectors,
  64 unique tickers; it has grown since the original 8)
- STRATEGY.md — the casino-coherent investment thesis
If a session begins and these files do not match what a prompt assumes,
STOP and report the mismatch. Do not "fix" them by overwriting.

Known drift, deliberately left alone: `STRATEGY.md` still describes the
original 8 sectors / ~55 tickers. `config/themes.yaml` is the live truth
(12 / 64). Do not reconcile them without an explicit instruction — both files
are canonical.
