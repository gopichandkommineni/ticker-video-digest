# `core/` — shared plumbing

The bits every other package needs. `core` deliberately **imports nothing else
from this repository** — that's what makes it safe for everyone to depend on.

---

## Contents

| File / folder | What it is |
|---|---|
| `config.py` | Reads settings and API keys from the environment |
| `cache.py` | Saves slow answers to disk so they aren't fetched twice |
| `models.py` | Data shapes shared across packages (Pydantic models) |
| `market/` | Market-wide indicators and the Reality Score |
| `social_media/` | Reddit and X clients |

## `market/` — the Market Reality Check

Powers `pages/03_Market_Reality_Check.py` and `python -m ticker_digest market`.

| File | Does |
|---|---|
| `fred_client.py` | Pulls US economic data from the St. Louis Fed (needs `FRED_API_KEY`) |
| `indicators.py` | Fetches the 14 individual indicators |
| `reality_score.py` | Combines them into one composite z-score |
| `thesis.py` | Asks Claude to write the narrative (needs `ANTHROPIC_API_KEY`) |

The composite splits into two buckets:

- **Market & sentiment** — Buffett indicator, CAPE proxy, margin debt,
  put/call ratio, Mag-7 concentration, RSP/SPY breadth, AAII sentiment
- **Real economy** — 10Y-2Y spread, industrial production, unemployment,
  jobless claims, core CPI, real retail sales, M2

**Positive score = the market is priced richer than the economy supports.
Negative = the market is discounting weakness.** VIX is displayed alongside but
deliberately excluded from the composite.

Without `FRED_API_KEY` the real-economy bucket switches off and the page still
works on market data alone.

The Claude thesis is cached by a hash of the indicator snapshot, so reloading
the page costs nothing until the underlying numbers change.

## `social_media/` — Reddit and X

| File | Does |
|---|---|
| `reddit/apewisdom_client.py` | Mention counts per stock. Free, no key. The main source. |
| `reddit/arctic_shift_client.py` | Community archive of actual posts. Free, no key. **Default backend.** |
| `reddit/apify_client.py` | Paid managed scraper. Alternative backend. |
| `reddit/client.py` | Direct Reddit API via `praw`. Mostly historical — see below. |
| `reddit/subreddit_discovery.py` | Which subreddits discuss a given stock? |
| `reddit/subreddit_match.py` | Match subreddits to companies by name |
| `reddit/subreddit_catalog.py` | Sweep the archive for finance subreddits |
| `reddit/ticker_resolver.py` | Ticker ↔ company name |
| `x/client.py` | X/Twitter client |

> ⚠️ **Reddit closed its public API in 2026** and put the rest behind
> Cloudflare. Direct fetches are unreliable and new API apps are gated, so the
> code routes through managed sources instead. Set `REDDIT_BACKEND` to choose.
> Read [docs/runbooks/reddit-local-runbook.md](../../docs/runbooks/reddit-local-runbook.md)
> before changing anything here.

## The rule for adding to `core`

Ask: *would a second, unrelated project want this?*

- **Yes** (an HTTP retry helper, a cache, a market indicator) → it belongs here.
- **No** (anything that knows about themes, the dashboard's tables, or how a
  page looks) → it belongs in `casino_dashboard`.

And never import `casino_dashboard` or `fintwit` from here. That creates a
circular dependency and breaks everything downstream.
