# `data/` — the saved results

> ## ⚠️ Read this before you touch anything here
>
> Both files in this folder are **live production data**, and both are
> **committed into git**. A robot updates them on a schedule and pushes the
> result to `main`.
>
> **Never commit a locally-modified copy.** Doing so overwrites months of real
> accumulated history with partial test output.

---

## The files

| File | Size | Holds | Written by | Committed? |
|---|---|---|---|---|
| `snapshots.db` | ~20 MB | The dashboard's data | `daily_refresh.yml`, 4× every weekday | **Yes** |
| `fintwit.db` | ~36 MB | The tweet archive | `fintwit-daily.yml`, nightly | **Yes** |
| `digests.db` | small | Your YouTube digest history | `./run digest RKLB`, when you run it | No — git-ignored |

All are **SQLite** databases: a complete database inside one ordinary file.
Nothing to install, nothing to start.

The warning above is about the first two. `digests.db` is yours: it only exists
if you've run a digest, it's git-ignored, and deleting it costs you nothing but
the memory of which YouTube claims you'd already seen (which is what makes the
next run's "what's new" meaningful). Point it somewhere else with
`TICKER_DIGEST_DB`.

## Why are databases committed to git?

Unusual, and deliberate. The dashboard is deployed on Streamlit Cloud, which
deploys straight from this repository. Committing the database is how freshly
computed numbers reach the deployed app — and it gives the data a full version
history for free.

The cost is the rule at the top of this page: two people (or a person and the
robot) writing the same file will conflict.

## What's inside `snapshots.db`

| Table | Holds |
|---|---|
| `ticker_snapshots` | One row per stock per day: open, high, low, close, volume |
| `signals` | Computed numbers: returns, RSI, distance from high/low |
| `social_mentions` | Reddit mention counts over time |
| `reddit_posts` | Actual post titles and text |
| `ticker_metadata` | Company name, market cap, next earnings date |
| `news_items` | Headlines per stock |
| `sector_heat` | Theme-level rollups |
| `etf_flows`, `sector_etf_mapping` | The money-flow inputs |
| `deal_log`, `manual_notes` | Loaded from `config/` |
| `congress_trades`, `congress_members`, `congress_member_committees` | Politician trading |
| `user_added_tickers`, `user_added_themes` | Added through the Add Stocks page |

Writes are **idempotent**: re-running the job for the same day overwrites that
day's row rather than adding a duplicate. So a re-run is always safe.

## Looking inside — safely

Reading is completely safe:

```bash
sqlite3 data/snapshots.db ".tables"
sqlite3 data/snapshots.db "SELECT ticker, close FROM ticker_snapshots ORDER BY date DESC LIMIT 10;"
```

`sqlite3` ships with macOS. To click around instead of typing SQL, use the free
[DB Browser for SQLite](https://sqlitebrowser.org/) — just don't press Save.

## What's inside `digests.db`

| Table | Holds |
|---|---|
| `digest_runs` | One row per digest you ran, with the whole run as JSON |
| `claims` | Every distinct claim heard about a ticker, and when it was **first** heard |
| `claim_citations` | Every video that made each claim, and which channel published it |
| `threads` | The generated threads, readable with `./run threads` |

`claims.first_seen_at` is never overwritten. That is how a later run knows a
claim isn't news any more.

`claim_citations` is why the digest can say "four of five videos said this",
and why a claim repeated by a channel that never said it before gets flagged
even though the claim itself is old. Counting *channels* matters: one
commentator posting three times is one source, not three.

## Testing changes to the data pipeline

Never against the real file. Use:

```bash
./run refresh
```

which copies `snapshots.db` to **`data/local-test.db`** and writes there.
`.gitignore` already ignores every `.db` in this folder *except* the two
production ones, so a throwaway copy can't be committed by accident.

## If you modified a production file by mistake

```bash
git status data/            # is it listed as modified?
git checkout data/snapshots.db   # throw away your local change
```

Do this **before** committing. If you already committed but haven't pushed, see
[docs/start-here/07-when-things-break.md](../docs/start-here/07-when-things-break.md#i-accidentally-changed-the-database).
If you already pushed, tell the repository owner rather than attempting a
force-push.

## Merge conflicts on these files

Common, because the robot commits constantly. There is no such thing as merging
two versions of a binary database — take the remote one:

```bash
git checkout data/snapshots.db
git pull
```

## A size warning

`fintwit.db` once grew past GitHub's 100 MB per-file limit, which blocked every
database-writing workflow until it was shrunk
(`scripts/shrink_fintwit_db.py` dropped the stored raw API payloads). Keep an
eye on the size before adding anything bulky.
