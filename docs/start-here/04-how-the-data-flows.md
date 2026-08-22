# 4. How the data flows

*Reading time: 8 minutes.*

This page follows a single number from the internet to your screen. Once you
have this picture, most of the code stops being mysterious.

---

## The one-picture version

```
   ┌──────────────────────────────────────────────────────────┐
   │  1. SOURCES on the internet                              │
   │     Yahoo Finance · ApeWisdom · Reddit archives ·         │
   │     FRED (US economy) · congressional disclosures         │
   └───────────────────────┬──────────────────────────────────┘
                           │  a robot downloads, 4× every weekday
                           ▼
   ┌──────────────────────────────────────────────────────────┐
   │  2. THE DAILY JOB                                        │
   │     src/casino_dashboard/jobs/daily_refresh.py           │
   │     fetch → calculate signals → save                     │
   └───────────────────────┬──────────────────────────────────┘
                           │  writes
                           ▼
   ┌──────────────────────────────────────────────────────────┐
   │  3. THE DATABASE — data/snapshots.db                     │
   │     one file, ~20 MB, committed back into git            │
   └───────────────────────┬──────────────────────────────────┘
                           │  reads (fast — no internet)
                           ▼
   ┌──────────────────────────────────────────────────────────┐
   │  4. THE DASHBOARD — app.py + pages/                      │
   └──────────────────────────────────────────────────────────┘
```

The key insight: **fetching and displaying are completely separate.** The
dashboard never waits on Yahoo Finance, because by the time you open it the
numbers are already sitting in a local file. That's why it feels instant, and
also why a stale dashboard means "the job failed", not "the dashboard is
broken".

---

## Step 1 — Where the numbers come from

| Source | What it gives | Costs money? |
|---|---|---|
| **Yahoo Finance** (via the `yfinance` library) | Daily prices, volume, company info, earnings dates | Free, no key |
| **ApeWisdom** | How often each stock is mentioned on Reddit | Free, no key |
| **Arctic Shift** | An archive of actual Reddit posts | Free, no key |
| **FRED** (St. Louis Fed) | Real-economy data: unemployment, CPI, yield curve | Free, needs a key |
| **Congressional disclosures** | Politicians' stock trades | Free |
| **Claude** (Anthropic) | The written market thesis | Paid, needs a key |

> **Why Reddit is complicated.** Reddit shut its public API in 2026 and put the
> rest behind Cloudflare. The project therefore reads *managed archives* rather
> than Reddit directly. If you touch anything Reddit-related, read
> [the Reddit runbook](../runbooks/reddit-local-runbook.md) first.

## Step 2 — The daily job, stage by stage

`src/casino_dashboard/jobs/daily_refresh.py` runs these in order. Each stage
reports success or failure into a summary you can read on GitHub:

1. **Universe** — read `config/themes.yaml`: which stocks am I watching?
2. **Price snapshots** — download prices and volume for all 64.
3. **Social mentions** — how much is each stock being talked about?
4. **Social mentions (per-subreddit)** — the same, split by community.
5. **Reddit posts** — pull actual post text for the most-discussed names.
6. **Ticker metadata** — company name, market cap, next earnings date.
7. **Manual notes** — load your hand-written notes from `config/manual_notes.yaml`.
8. **Signals** — do the maths (see below).
9. **ETF flows** — is money moving into the ETFs that represent each theme?
10. **Deal log** — load the deals you recorded in `config/deal_log.yaml`.
11. **Sector heat** — roll all of the above up from stocks to themes.
12. **Congress data** — refresh politicians' disclosed trades.
13. **User-added ticker retries** — retry stocks added via the Add Stocks page
    whose first download failed.

**Each stage is wrapped in its own error handler.** If ApeWisdom is down, that
stage records a failure and the other twelve carry on. One broken source never
takes down the whole refresh — that's deliberate.

## Step 3 — What a "signal" actually is

A signal is just a number the job calculates once and stores, so the dashboard
doesn't have to. Nothing here is exotic — it's arithmetic on price history:

| Signal | Plain English |
|---|---|
| Return over N days | How much has the price changed in the last week / month / year? |
| Distance from high | How far below its 52-week peak is it? |
| Distance from low | How far above its 52-week bottom? |
| RSI | A standard 0–100 momentum gauge. High = ran up fast recently. |
| Volume spike | Is today's trading unusually busy versus normal? |
| Mention change | Is Reddit chatter rising or falling? |

The code lives in `src/casino_dashboard/signals/`:
`computers.py` does the maths, `orchestrator.py` runs it for every stock, and
`sector_aggregator.py` rolls stock-level numbers up into theme-level scores.

## Step 4 — Where it's stored

One file: `data/snapshots.db`. Inside it, one table per kind of thing:

| Table | Holds |
|---|---|
| `ticker_snapshots` | One row per stock per day: open, high, low, close, volume |
| `signals` | The computed numbers above |
| `social_mentions` | Reddit mention counts over time |
| `reddit_posts` | Actual post titles and text |
| `ticker_metadata` | Company name, market cap, earnings date |
| `sector_heat` | Theme-level rollups |
| `etf_flows`, `deal_log`, `manual_notes` | The money-flow and note inputs |
| `congress_trades`, `congress_members`, `congress_member_committees` | Politician trading |
| `user_added_tickers`, `user_added_themes` | Anything added via the Add Stocks page |

Writes are **idempotent** — running the job twice for the same day overwrites
that day's row rather than adding a duplicate. So a re-run is always safe.

## Step 5 — Onto the screen

A page in `pages/` calls a loader in `src/casino_dashboard/ui/loaders.py`, which
queries the database and hands back a table. The page formats it and draws it.
No page fetches from the internet — with one exception: the Add Stocks page,
which has to check a brand-new ticker exists before accepting it.

---

## Who runs all this, and when

Nobody runs it by hand. GitHub runs it on a timer.

`.github/workflows/daily_refresh.yml` fires at **2am, 9am, 1pm and 5pm US
Eastern** on weekdays (plus 2am at weekends), and each time it:

1. Checks out the repository
2. Installs the project
3. Runs `python -m casino_dashboard.jobs.daily_refresh`
4. **Commits the updated `data/snapshots.db` back to `main`**

Step 4 is the unusual one, and it's why the rule "never commit the database
from your laptop" matters so much: you and the robot would be fighting over the
same file, and the robot's version is the real one.

The four times were chosen around the US trading day: overnight, pre-market,
mid-session, and after the close.

All the workflows share a lock called `db-writer`, so two jobs can never write
the database at the same time. A second job waits its turn instead.

## Where the secrets live

The job needs API keys, and they are **not** in the code. They're stored as
GitHub Actions *secrets* — encrypted values only the workflow can read, visible
to nobody, not even in the logs. On your laptop the same values go in a `.env`
file that git ignores.

There is exactly one rule: **no key ever gets typed into a `.py` or `.yaml`
file.** Code reads keys from the environment, always.

---

## How to tell whether it's working

1. Go to the **Actions** tab on GitHub.
2. Open the most recent "Daily Refresh" run.
3. The **Summary** tab shows the stage-by-stage report — a ✓ or ✗ per stage.

A green run with several ✗ stages is normal-ish (a flaky source). A dashboard
showing week-old prices means the job hasn't succeeded in a week, and that's
worth investigating — see [When things break](07-when-things-break.md).

---

**Next:** [5. Glossary →](05-glossary.md)
