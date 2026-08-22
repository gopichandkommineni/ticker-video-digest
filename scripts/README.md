# `scripts/` — one-off commands a human runs

Nothing here runs on its own schedule as part of normal operation. These are
either **maintenance commands** invoked by a manual GitHub workflow, or
**migrations** that have already been applied and are kept only for the record.

Day-to-day work needs `./run` at the repository root, not this folder.

---

## Operational — still used

| Script | Run by | Does |
|---|---|---|
| `run_daily.py` | `fintwit-daily.yml`, nightly | Fetch yesterday's tweets for every tracked handle |
| `run_backfill.py` | `fintwit-backfill.yml`, manual | Fill in history for one or more handles |
| `run_variance.py` | `fintwit-variance.yml`, manual | Ask both tweet providers the same question N times and compare — do they return consistent data? |
| `import_probe_data.py` | By hand | Load already-paid-for probe JSON into the database instead of re-fetching it |

> 💸 `run_backfill.py` spends real money — the tweet providers are metered.
> Check the date range twice before starting one.

## Maintenance — occasional

| Script | Run by | Does |
|---|---|---|
| `cleanup_corrupt_news.py` | `cleanup_corrupt_news.yml`, manual | Delete news rows corrupted by an old parser bug |
| `shrink_fintwit_db.py` | By hand / before a backfill | Drop stored raw API payloads to keep `fintwit.db` under GitHub's 100 MB file limit |

## Migrations — already applied, kept for the record

Do **not** re-run these casually. They're documented history, and each is
idempotent so an accidental second run is survivable, but there's no reason to.

| Script | Applied | Spec |
|---|---|---|
| `migrate_ingestion_ledger_v1.py` | Yes | [ingestion-ledger-gaps-v1](../docs/specs/ingestion-ledger-gaps-v1.md) |
| `migrate_worker_pool_v1.py` | Yes | [ingestion-worker-pool-v1](../docs/specs/ingestion-worker-pool-v1.md) |

---

## Before running anything here

1. **Read the docstring at the top of the file.** Every script explains what it
   does and how to invoke it. They're accurate.
2. **Check whether it writes a git-tracked database.** `data/snapshots.db` and
   `data/fintwit.db` are production data — see
   [`data/README.md`](../data/README.md).
3. **Prefer the GitHub workflow.** If a manual workflow exists for the script,
   use it (Actions tab → the workflow → *Run workflow*). It has the right
   secrets, the right environment, and it queues behind the `db-writer` lock so
   it can't collide with another job.

## Adding a script

- Start with a docstring: what it does, exactly how to run it, and whether it's
  safe to re-run.
- Say plainly if it's destructive or costs money.
- Make it idempotent if you can — running twice should be harmless.
- Add a row to the right table above.
