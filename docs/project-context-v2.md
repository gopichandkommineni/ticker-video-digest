# Casino-Coherent Momentum Dashboard — Project Context v2

**Last updated:** 2026-05-16 (end of long planning session)
**Owner:** AG (Gopi Kiran Kommineni)
**Status:** Production-stable, multiple features queued, none in active build
**Repo:** github.com/gopichandkommineni/ticker-video-digest
**Deployment:** Streamlit Cloud, daily GitHub Actions refresh at 13:00 UTC

---

## Purpose of this document

This is the durable handoff context for resuming dashboard work in fresh
conversations. It anchors on the 12-step data pipeline that defines the
system, captures architectural decisions, and lists open work in priority
order. When starting a new chat, point Claude at this doc first.

The pipeline is the dashboard's contract. Everything in scope serves it.
Everything else is deferred or rejected.

---

## The 12-step pipeline (the canonical architecture)

This is the dashboard, end to end:

1. **Config defines which tickers and sectors exist.**
   `config/themes.yaml` is the source of truth. 54 tickers across 8
   sectors. All other steps read from this.

2. **yfinance fetches 2 years of OHLCV + 5 news articles per ticker,
   in parallel.** ThreadPoolExecutor for parallelism. Raw price history
   and recent news stored in `ticker_snapshots` and `news_items`.

3. **ApeWisdom fetches social mention counts and 24h deltas.**
   Stored in `social_mentions`. Currently the only social signal source.

4. **yfinance info fetches fundamentals.** Short interest, analyst price
   targets, earnings dates, ownership. Stored in `ticker_metadata`
   (15 fields total). Requires lxml for earnings_dates parsing.

5. **YAML loads curated catalysts, red flags, and deal log.** Manual
   curation in YAML files; loaded at refresh time. The deal log feeds
   sector-level capital flows (step 7/8). User commitment to weekly
   updates is an open question.

6. **Signal computers transform raw history into 13 technical and
   social signals per ticker.** Includes return_1m/ytd/1y, rsi_14,
   vol_ratio_30d, apewisdom_velocity, plus derived signals.
   Stored in `signals`.

7. **ETF fetcher converts AUM changes into implied capital flows
   per sector.** Calculated-from-AUM approach (no scraping in v1).
   Photonics has no ETF and shows "n/a". Stored in `etf_flows`.

8. **Sector aggregator equal-weights per-ticker signals up to 7
   sector-level metrics across 3 dimensions.** Capital Flows, Hype,
   Stock Growth — shown separately, never combined into a composite.
   Stored in `sector_heat`. Skip-on-null behavior for missing constituents.

9. **Indicator fetchers pull 14 macro indicators and z-score each
   against 5-year history.** FRED API + yfinance + free sources.
   Covers valuation, real economy, decoupling, retail froth.

10. **Reality Score folds 14 z-scores into one composite number and
    one of 4 bands.** Single broader-market gauge: Cheap / Normal /
    Stretched / Bubble (or equivalent).

11. **Claude (3 passes) extracts video insights, synthesizes a digest,
    and generates a macro thesis.** AWS Bedrock or Anthropic API.
    Output cached, not regenerated per page load.

12. **Streamlit reads all results from SQLite (cached, no live calls)
    and renders 4 pages.** Pages: Homepage / Sector Ranking /
    Per-Ticker Detail / Macro Reality. No live API calls in render
    path — the daily refresh is the only writer.

---

## What's shipped (in production)

- Steps 1–6 fully implemented and tested
- Database: SQLite at `data/snapshots.db`, committed to main, ~500 days
  history
- Tables: `ticker_snapshots`, `signals`, `news_items`, `social_mentions`,
  `ticker_metadata`, `manual_notes`
- Daily refresh: GitHub Actions cron 13:00 UTC, includes lxml dependency
- 16 signals computed daily (the original 13 plus 3 derived added later)
- Per-ticker detail page (`pages/02_Ticker_Detail.py`) implemented to
  spec v1
- 263 passing tests
- Live and being used by a 5-person team

---

## What's specced but not built

### Sector ranking (steps 7–8 of the pipeline)
- Spec: `docs/sector-ranking-spec-v2.md`
- Three dimensions shown separately: Capital Flows, Hype, Stock Growth
- 5-phase build estimate (6–9 days calendar time)
- **Gated on 8 open questions in §8 of the spec.** Don't begin
  implementation until answered. Critical ones: ETF mapping accuracy,
  Photonics no-ETF handling, deal log maintenance commitment, nav
  placement.
- Claude Code prompt written in prior session, in chat transcript

### TradingView Technical Analysis widget
- Spec revision needed: per-ticker-page-spec-v1 → v2 (adds widget,
  revises v1's "no charts" decision)
- Embed TradingView's official free Technical Analysis widget below
  Tier 3 tiles on per-ticker page
- Single PR, ~50–100 lines, ~1 evening of work
- $0 cost, no auth, real-time during market hours
- Claude Code prompt written in prior session, in chat transcript

### Broader-market reality-check (steps 9–10)
- Researched but not specced
- Four panels: Valuation (Buffett indicator, Shiller PE), Real Economy
  (yield curves, Sahm Rule, NFCI), Decoupling Gauge (SPX vs earnings/
  GDP/M2), Retail Froth (margin debt, put/call, AAII, 0DTE %)
- $0/month using FRED API + yfinance + free sources
- 10–15 days for all 4 panels, or 3 days for Valuation + Real Economy alone
- LLM macro narrative score is the bridge to step 11

### Layer 2 narrative DD (part of step 11)
- LLM narrative analysis using ticker_events and measured market reactions
- Button on per-ticker page to trigger fresh DD, cache result
- Scope undefined; needs spec before build

### Social mentions expansion (extends step 3)
- Current: ApeWisdom only (mention counts + 24h deltas)
- Proposed: add per-ticker Reddit and StockTwits mentions for richer
  signal layer
- Architecture decided (this session): MentionFetcher abstract base
  class, one file per source under `src/casino_dashboard/data/social/`,
  graceful degradation on fetcher failure
- **Tooling decision deferred — see "Social mentions tooling decision"
  below**
- 7–9 days for v1 (raw fetch + filters + daily aggregator + UI)

---

## What's evaluated and rejected

### Agent-Reach as a library dependency
- Repo: github.com/Panniantong/Agent-Reach (19.5k stars, 1.7k forks,
  249 commits, active community)
- **Decision: do not adopt as dependency.** Agent-Reach is an installer
  and health checker for upstream tools, not a data extraction library.
  Channel files implement `can_handle()` and `check()` only — no
  `fetch()` or `read()`. The actual scraping is done by separate CLIs
  (twitter-cli, rdt-cli, yt-dlp, etc.) that Agent-Reach delegates to.
- **Patterns worth stealing (already captured in social fetcher
  architecture):**
  - Tier 0/1/2 channel system for "zero config" / "needs key or login" /
    "complex setup"
  - `(status, message)` return contract for health checks, with fix
    commands in the message
  - Cookie acquisition fallback chain (saved config → live browser via
    rookiepy → anonymous fallback)
  - `format_xhs_result`-style response normalizer that strips bloated
    API responses to ~10 essential fields
- Reference files to read if questions arise: `channels/v2ex.py`
  (clean public-API pattern), `channels/xueqiu.py` (auth + cookie
  pattern), `channels/xiaohongshu.py` (response normalizer pattern),
  `channels/base.py` + `doctor.py` (tier/status pattern)

### Vercel/Next.js rewrite of dashboard
- Researched, deferred. Vercel is host, not UI improver. Streamlit
  constraints are real (column heights, dark mode) but the known UI
  bugs would exist in any framework. Not a priority.

### Composite "heat score" combining the 3 sector dimensions
- Explicitly rejected. The spec's whole point is showing dimensions
  separately so users can see Capital / Hype / Growth divergence.
  A composite hides the signal.

---

## Social mentions tooling decision (open)

This was the active topic at end of last session. Spec depends on it.

### What we evaluated

**twitter-cli (public-clis/twitter-cli)**
- 2.1k stars, 133 commits, 32 tagged releases, 10 contributors
- Apache 2.0, on PyPI (`pip install twitter-cli`)
- Real anti-detection engineering: curl_cffi TLS fingerprint
  impersonation, dynamic Chrome version matching, header alignment,
  request timing jitter, full cookie forwarding
- Structured `--yaml`/`--json` output with documented schema (SCHEMA.md)
- CI on Python 3.8/3.10/3.12
- **Genuine concerns:** ToS violation, GraphQL endpoint drift causes
  periodic 404s on `search` command, datacenter IPs get flagged, account
  ban risk for sustained patterns
- **Recommended setup if used:** burner Twitter account (never main),
  residential proxy via `TWITTER_PROXY` env var (~$1/mo Webshare),
  accept periodic breakage

**rdt-cli (public-clis/rdt-cli)**
- 306 stars, 16 commits, 6 tagged releases
- Same maintainer and architecture as twitter-cli
- Apache 2.0, on PyPI (`pip install rdt-cli`)
- Chrome 133 fingerprint consistency, Gaussian jitter, exponential
  backoff, 7-day cookie TTL with auto-refresh
- Stable envelope output: `ok / schema_version / data / error`
- **Bridge tool until PRAW approval lands.** PRAW is the official path
  and strictly better when available; rdt-cli is the interim solution.

**StockTwits free API**
- Direct HTTP, no auth, no ToS issues, zero fragility
- Cashtag mentions with user-applied bullish/bearish sentiment tags
- Lower volume than Twitter but explicitly stock-focused signal
- Recommended as either primary (if skipping Twitter) or graceful
  fallback (if twitter-cli is primary)

**Earlier rejected as primary path:**
- Official Twitter API: $200/mo for Basic tier, real reliability but
  bad cost-quality tradeoff for personal dashboard
- Direct cookie scraping built in-house: don't reinvent what twitter-cli
  and rdt-cli already do better

### The actual decision (still open)

The question that gates the social mentions spec:
**Are you willing to manage a burner Twitter account + residential
proxy ($1/mo) for twitter-cli, sustained over months?**

- **Yes** → twitter-cli + rdt-cli (with PRAW migration when approved)
  + StockTwits as fallback. Best signal quality.
- **No** → rdt-cli + StockTwits only, skip Twitter. Lower signal, zero
  ops overhead.
- **Defer** → Write spec with both options documented, decide at build
  time.

This decision was unanswered when the chat was rolled over.

---

## Known production bugs (deferred, not fixed)

1. **`nan` rendered in empty Catalyst/Red Flag tiles on desktop.**
   pandas NaN→string coercion in tile rendering. Per-ticker page.

2. **Dark mode tile backgrounds stay light.** Hardcoded CSS doesn't
   respect Streamlit theme. Per-ticker page.

3. **`-0.0%` sign formatting on near-zero changes.** Should display
   `0.0%` or `0%`. Multiple places.

All three: small fixes, deferred because new feature work has consistently
been prioritized. Fixing all three is probably one focused evening of work.

---

## Active queue (priority order)

This order is what we landed on at end of last session. Don't reshuffle
without explicit reason.

1. **TradingView widget integration** (small, ~1 evening, prompt written)
2. **Sector ranking 5-phase build** (6–9 days, prompt written, gated on
   §8 questions in spec)
3. **Fix the 3 known production UI bugs** (small)
4. **Rip pattern analysis v2** (control group + de-overlap + 9 missing
   tickers — see `docs/rip-pattern-analysis-v1.md`)
5. **Social mentions integration** (rdt-cli + StockTwits ± twitter-cli;
   7–9 days; needs tooling decision first; needs spec)
6. **Broader-market reality-check dashboard** (steps 9–10; 10–15 days
   full or 3 days for partial)
7. **Layer 2 narrative DD** (part of step 11; scope undefined)
8. **Options data integration** (deferred decision; $0 / $30/mo / $100+/mo
   paths)

---

## Repo conventions

- **Specs are durable, code is throwaway.** Specs in `docs/` survive
  context resets; code can be rebuilt from specs.
- **Verify before declaring done.** Tests passing is necessary, not
  sufficient. Always `streamlit run` locally before merging UI PRs.
  This rule was learned the hard way after the per-ticker page
  ImportError shipped to production with 85 passing unit tests.
- **One feature per PR.** Sector ranking is 5 separate PRs across 5
  phases. Don't bundle.
- **Don't build past hour 8 of focused work.** Late-night work has
  consistently shipped bugs.
- **Don't merge a Claude Code PR you haven't locally run.**
- **YAML for curated content, Python for computed signals, SQLite for
  storage, Streamlit for render.** Don't blur these layers.
- **Manual curation is a feature, not a workaround.** The deal log,
  catalysts, and red flags are deliberately human-maintained.
- **No live API calls in the render path.** Daily refresh writes;
  Streamlit reads cached results.

---

## Files that anchor the project

When starting a new chat, point at these:

- `docs/project-context-v2.md` — this file
- `docs/per-ticker-page-spec-v1.md` — locked spec for the detail page
- `docs/sector-ranking-spec-v2.md` — draft spec, gated on §8 questions
- `docs/rip-pattern-analysis-v1.md` — empirical findings, hypothesis-level
- `config/themes.yaml` — canonical universe definition
- `CLAUDE.md` — repo conventions for Claude Code

Existing in chat transcripts but not yet in repo:
- Two written Claude Code prompts (TradingView widget, sector ranking
  5-phase build)
- This session's social mentions architecture (MentionFetcher base class,
  fetcher pattern, graceful degradation)

---

## How to start the next chat

Open new conversation. First message:
