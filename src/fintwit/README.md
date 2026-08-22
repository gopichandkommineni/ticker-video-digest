# `fintwit/` — the tweet archive

A self-contained pipeline that downloads posts from a list of finance accounts
on X ("FinTwit") and stores them in `data/fintwit.db`.

**It is separate from the dashboard.** Its own database, its own scheduled
jobs, its own entry points. The dashboard doesn't read it. You can ignore this
whole folder while working on the dashboard, and vice versa.

Status: live and running, but nothing consumes the archive yet. It's being
built up so a future feature has history to work with.

---

## Sub-folders

| Folder | Does |
|---|---|
| `tweet_sources/` | Talks to the tweet providers. One file per provider. |
| `storage/` | Reads and writes `data/fintwit.db` |
| `orchestration/` | Decides what to fetch, when, and how fast |

### `tweet_sources/` — the providers

X's own API is expensive, so the pipeline buys from resellers and can switch
between them. Set `TWEET_PROVIDER` to choose.

| File | Provider |
|---|---|
| `getxapi.py` | GetXAPI (`GETXAPI_KEY`) |
| `twitterapi.py` | twitterapi.io (`TWITTERAPI_IO_KEY`) |
| `factory.py` | Picks one based on `TWEET_PROVIDER` |
| `base.py` | The interface every provider must implement |
| `compare.py` | Runs both and diffs the results — used by the variance probe |
| `_http.py` | Shared HTTP with retries |

To add a provider: implement `base.py`'s interface, register it in
`factory.py`. Nothing else changes.

### `storage/`

| File | Does |
|---|---|
| `db.py` | Creates the schema. Idempotent. |
| `tweets.py` | Saving and reading tweets |
| `handles.py` | The list of accounts being tracked, and their state |
| `day_log.py` | The ledger: which (handle, day) pairs have been fetched, and how they went |
| `reads.py` | Query helpers |

`day_log` is the important idea. Every account-day is a row with a status, so
the pipeline knows exactly what's missing and can resume after any interruption
without refetching what it already has.

### `orchestration/`

| File | Does |
|---|---|
| `runner.py` | Top-level "fetch everything that's due" |
| `day_fetcher.py` | Fetches one account-day |
| `worker_pool.py` | Runs several fetches in parallel |
| `rate_limiter.py` | Stays under the provider's request cap |
| `reconciler.py` | Finds and reopens gaps in the ledger |
| `config.py` | Tunables |

---

## Running it

```bash
python -m fintwit.storage        # storage entry point
python -m fintwit.tweet_sources  # provider entry point
```

In practice these run via `scripts/` and GitHub Actions, not by hand:

| Workflow | Trigger | Runs |
|---|---|---|
| `fintwit-daily.yml` | 2am ET daily | `scripts/run_daily.py` — fetch yesterday |
| `fintwit-backfill.yml` | Manual | `scripts/run_backfill.py` — fill history for a handle |
| `fintwit-schedule.yml` | Manual | Pause or resume the daily ingest |
| `fintwit-variance.yml` | Manual | `scripts/run_variance.py` — compare providers |

It shares the `db-writer` lock with the dashboard's jobs, so the two never
write git-tracked databases at the same time.

---

## Design docs

- [Ingestion ledger gaps v1](../../docs/specs/ingestion-ledger-gaps-v1.md) — the day-log design (shipped)
- [Ingestion worker pool v1](../../docs/specs/ingestion-worker-pool-v1.md) — parallel fetching
- [PR B cutover plan](../../docs/specs/pr-b-cutover-plan.md) — moving production onto the pool
- [Variance probe results](../../research/probes/variance/README.md) — do providers return consistent data?

## Things to know before you touch it

- `data/fintwit.db` is **~36 MB and committed to git**, like the dashboard's
  database. Never commit a locally-modified copy.
- It once outgrew GitHub's 100 MB file limit and had to be shrunk
  (`scripts/shrink_fintwit_db.py`). Keep an eye on the size.
- Provider APIs are metered. Careless backfills cost real money — check the
  date range twice before starting one.
