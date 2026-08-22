# Ingestion Worker Pool — v1

**Project:** ticker-video-digest / FinTwit ingestion
**Date drafted:** 2026-06-20
**Status:** Spec for review. Not yet implemented.
**Owner:** AG
**Predecessor:** `docs/specs/ingestion-ledger-gaps-v1.md` (shipped, merged via PR #99/#100)
**Companion:** `docs/specs/ingestion-behavioral-audit-v1.md` (the source of the gap list below)

---

## 1. Context

The ingestion layer today processes work sequentially. `run_days` is a
`for` loop with `time.sleep` between calls; no concurrency primitive
exists. At 10 handles × daily delta this is fine. At 30-40 handles ×
180-day backfill it is not — a single backfill run would take roughly
8-10 hours, comfortably past the GitHub Actions 6-hour job cap.

The behavioral audit (`docs/specs/ingestion-behavioral-audit-v1.md`) found
that the data model is ready for a worker pool but the execution model
is missing. Ledger v1 introduced the columns (`next_eligible_at`,
`reached_floor`, `error_class`) and status vocabulary (`fetching`,
`complete`, `exhausted`) the pool needs, but none of those code paths
fire today. This spec fills in the execution model against the
already-locked data model.

The spec also folds in four call-site corrections the audit surfaced
as B5 and B7 partials. They are strictly speaking sequential-code
bugs, but the worker is the natural caller for the fixes, so bundling
them here is the right scope.

This spec is **additive in code, near-additive in schema** (two new
columns), and changes the meaning of one existing column
(`tweet_count` → `tweets_fetched` + `tweets_written`).

## 2. Decisions locked in the planning chat

| # | Decision | Choice |
|---|----------|--------|
| 1 | WAL transition | Separate pre-PR before worker pool |
| 2 | `tweet_count` semantics | Two new columns (`tweets_fetched`, `tweets_written`); legacy `tweet_count` deprecated but retained |
| 3 | Per-provider concurrency | 5 workers for twitterapi.io, 3 for getxapi |
| 4 | Backoff schedule | 60s after attempt 1, 5min after attempt 2, 30min after attempt 3, then `failed` |
| 5 | Atomic claim | `BEGIN IMMEDIATE` + conditional `UPDATE` on `(status='pending', attempts < max)` |
| 6 | `reached_floor` consumption | Call site reads the flag; sets `complete` (true) or `exhausted` (false) |
| 7 | Rate-limited partial behavior | Mark `failed` with `error_class='rate_limit'` and `next_eligible_at`, not `ok` |
| 8 | `error_class` populated | Every failure write sets this column |

## 3. Architecture

### 3.1 Components

```
config (handles + date range)
        │
        ▼
populate_pending_days()             [existing, audit confirmed working]
        │
        ▼ writes status='pending' rows into day_fetch_log
        │
day_fetch_log  ◄──┐
        │         │ ledger = queue (transactional outbox pattern)
        ▼         │
worker dispatcher │
        │         │
        ▼         │
┌─────────────────┴─────────────────┐
│  Per-provider thread pools         │
│    twitterapi.io: 5 workers        │
│    getxapi:       3 workers        │
└─────────────────┬─────────────────┘
                  │ per-day fetch with rate limiting
                  ▼
        provider adapter (paginated)
                  │
                  ▼ FetchResult(tweets, reached_floor)
                  │
        upsert_tweets()             [existing, ledger v1 updated]
                  │
                  ▼ writes raw_tweets + tweet_provenance
                  │
        mark_day_outcome()          [new — wraps existing mark_day]
                  │
                  ▼ writes status, counts, error_class, next_eligible_at
```

### 3.2 Why database-as-queue, not an external broker

The audit confirms the existing ledger already functions as a work
queue — `get_pending_days` and `get_retryable_days` return slices of
work the sequential loop consumes today. A worker pool consumes the
same queue. This is the transactional outbox pattern; it works because:

- Single writer per ledger row (the worker that claimed it)
- Idempotent storage layer (`tweet_id` PK absorbs duplicates)
- Latency tolerance is high (daily refresh, not real-time)
- Workload size is small (~7,200 jobs for a 40-handle backfill)

No external broker (Redis, RabbitMQ, Kafka) is justified at this scale.
A worker pool with the ledger as queue gives us bounded concurrency,
durability across process crashes, and replayability — without
introducing infrastructure that would not pay for itself.

### 3.3 Concurrency model

`concurrent.futures.ThreadPoolExecutor`, one pool per provider, sizes
from §2 decision 3. Workers are blocking — they do HTTP I/O via the
existing adapters, which are synchronous. We do not migrate to asyncio
in this PR; the perf difference at this scale is negligible.

Per-provider rate limiting via a `RateLimiter` class with a
`threading.Lock` and a minimum-interval-between-calls. Starting
intervals: 200ms for twitterapi.io, 500ms for getxapi. Tunable.

### 3.4 The claim protocol

A worker claims a pending row via:

```python
with conn:                                    # autocommit on success
    conn.execute("BEGIN IMMEDIATE")
    cursor = conn.execute("""
        UPDATE day_fetch_log
        SET status = 'fetching',
            attempts = attempts + 1,
            first_attempted_at = COALESCE(first_attempted_at, ?),
            last_attempted_at = ?
        WHERE handle = ? AND date = ? AND provider = ?
          AND status IN ('pending', 'failed')
          AND attempts < ?
          AND (next_eligible_at IS NULL OR next_eligible_at <= ?)
    """, (now, now, handle, date, provider, MAX_ATTEMPTS, now))
    claimed = cursor.rowcount == 1
```

`BEGIN IMMEDIATE` acquires the write lock immediately rather than
deferring it to the first write. Two workers trying to claim the same
row will serialize: the first wins, the second sees `rowcount == 0`
and moves on. No double-claims possible.

WAL mode is required for this protocol to be non-blocking against
concurrent readers. WAL is enabled by the pre-PR (separate change,
runs before this work lands).

### 3.5 The fetch and outcome protocol

After claiming, the worker:

1. Calls the existing provider adapter, which paginates internally
   and returns `FetchResult(tweets, reached_floor)`.
2. Calls the existing `upsert_tweets` with the tweet list. Captures
   the *rows-written* count returned by the upsert (a new return
   value — see §4.3).
3. Determines outcome status from `reached_floor`:
   - `True` → `complete`
   - `False` → `exhausted`
4. Calls `mark_day_outcome` (new function wrapping existing
   `mark_day`) to write the final ledger row.

On exception during steps 1-2:

- If the exception class maps to `rate_limit` (HTTP 429): mark `failed`
  with `error_class='rate_limit'`, `next_eligible_at` per the backoff
  schedule. Commit any partial tweets that did land (idempotent —
  `INSERT OR IGNORE`).
- If the exception is transient (`timeout`, `network`): same as above
  with appropriate `error_class`.
- If the exception is permanent (`auth`, `parse`): mark `failed`
  immediately with `attempts = MAX_ATTEMPTS` to skip retries.
- If `attempts >= MAX_ATTEMPTS` after this attempt: stay `failed`,
  no `next_eligible_at` (terminal).

The key behavioral change from today: **a rate-limited partial fetch
is no longer marked `ok`.** It is marked `failed` with backoff. The
next worker picks it up after cooldown and re-runs the window from
scratch (or from a saved cursor — see §6).

### 3.6 Reconciliation step

Today, two providers fetch the same window and `mark_day` writes
`ok`/`mismatch` based on count agreement. After the worker pool, this
becomes a separate post-pool step:

```python
def reconcile_completed_days():
    """For each (handle, date) where BOTH providers reached a terminal
    single-provider status (complete/exhausted), overwrite the rows'
    status with 'ok' (counts agree) or 'mismatch' (counts disagree).
    """
```

This preserves the existing reconciliation semantics: `ok`/`mismatch`
remain the cross-provider verdict; `complete`/`exhausted` are the
single-provider outcomes that feed it.

`failed` rows are not reconciled — they retry first.

## 4. Schema changes

### 4.1 Two new columns on `day_fetch_log`

```sql
ALTER TABLE day_fetch_log ADD COLUMN tweets_fetched INTEGER;
ALTER TABLE day_fetch_log ADD COLUMN tweets_written INTEGER;
```

- `tweets_fetched`: count returned by the provider (what current
  `tweet_count` records today).
- `tweets_written`: count of rows actually inserted into `raw_tweets`
  (excludes dedupe-hits).

The legacy `tweet_count` column stays. The migration copies its values
into `tweets_fetched` for backwards compatibility, and from this PR
forward both new columns are populated by the worker.

### 4.2 No other schema changes

Everything else the worker pool needs already exists in `day_fetch_log`
from ledger v1: `next_eligible_at`, `error_class`, `reached_floor`,
`first_attempted_at`, `last_succeeded_at`, the dispatch index, and
the full status vocabulary.

### 4.3 `upsert_tweets` return-value change

```python
# before
def upsert_tweets(conn, handle, tweets, provider) -> None: ...

# after
def upsert_tweets(conn, handle, tweets, provider) -> int:
    """Returns the number of rows actually inserted (excludes
    duplicates ignored by INSERT OR IGNORE)."""
```

Existing callers ignoring the return value continue to work. The
worker uses it to populate `tweets_written`.

## 5. Implementation outline

### 5.1 New files

- `orchestration/worker_pool.py` — the pool, dispatcher, claim loop.
- `orchestration/rate_limiter.py` — `RateLimiter` class with lock +
  monotonic-time tracking.
- `orchestration/reconciler.py` — the post-pool reconciliation step.

### 5.2 Modified files

- `storage/day_log.py` — add `claim_day` (the atomic claim), add
  `mark_day_outcome` (the new wrapper). Existing `mark_day` stays for
  backwards compat.
- `storage/tweets.py` — `upsert_tweets` returns inserted count.
- `tweet_sources/_http.py` — wire in the rate limiter.
- `orchestration/runner.py` — `run_days` becomes a thin wrapper that
  dispatches to the worker pool. Sequential mode kept as a fallback
  via a `--sequential` flag for debugging.
- `orchestration/config.py` — add `WORKER_POOL_SIZES`,
  `RATE_LIMITER_INTERVALS_MS`, `MAX_ATTEMPTS`, `BACKOFF_SCHEDULE_SEC`.

### 5.3 Defaults (from §2 decisions 3 and 4)

```python
WORKER_POOL_SIZES = {
    "twitterapi": 5,
    "getxapi":    3,
}
RATE_LIMITER_INTERVALS_MS = {
    "twitterapi": 200,
    "getxapi":    500,
}
MAX_ATTEMPTS = 3
BACKOFF_SCHEDULE_SEC = [60, 300, 1800]   # 60s, 5min, 30min
```

### 5.4 GitHub Actions runtime handling

A backfill at 40 handles × 180 days = 7,200 jobs. At an average of 2s
per job through twitterapi at 5 workers (~5 jobs/sec sustained, less
when rate-limited), backfill is roughly 25-50 minutes. Comfortably
within the 6-hour Actions cap.

If a backfill ever exceeds the cap, the existing ledger-as-queue
pattern recovers it automatically: next run picks up the still-pending
rows. No explicit chunking needed.

## 6. Deferred decisions, named explicitly

These come up naturally in design but are deliberately deferred:

- **Within-window resume on retry.** A retry currently re-fetches the
  full window. A future enhancement: save a cursor/since_id at the
  page level so retries pick up where they failed. Not in v1 because
  the perf cost of full re-fetch at our scale is small and the
  complexity cost is real. The `last_page_token` column is already in
  the schema from ledger v1; it stays unused for now.
- **Adaptive pool sizing.** Sizes are static in v1. A future enhancement
  could scale workers down when 429s rise and back up when they fall.
  Not in v1 because we have no measurements yet.
- **Cross-process worker pool.** All workers are threads in one
  process. Multi-process (different machines) would need a real
  message queue. Not in v1 because we have no need.
- **Variance probe integration.** The probe runner could become a job
  kind in the worker pool with a `job_kind='probe'` tag. Not in v1 —
  variance keeps its existing sequential path; pool work is production
  only. The audit confirmed variance writes through `upsert_tweets`
  correctly, so it inherits the schema changes.

## 7. Out of scope — DO NOT BUILD

- Worker-pool support for ad-hoc single-ticker refresh (the
  `user_added_tickers` background thread from the casino_dashboard
  side). Separate concern, separate DB, not part of this PR.
- Any UI for monitoring the worker pool. Logs and the ledger itself
  are the v1 monitoring surface.
- Migrating the variance probe runner to use the pool.
- Migrating the per-ticker dashboard refresh to use the pool.
- Splitting `tweets_watermark_utc` on `handles` into per-provider
  watermarks. Noted as recommended in project context but defers to
  a later PR.
- WAL mode pragma. The pre-PR handles this.
- Any change to `casino_dashboard/` or `ticker_digest/`.

## 8. Tests required

### Concurrency tests (the highest-value tests in this PR)

- **Single-row claim is exclusive.** Spin up 10 threads racing to
  claim the same (handle, date, provider). Exactly one succeeds; nine
  see `rowcount == 0`. Test with `BEGIN IMMEDIATE`.
- **Different rows can be claimed in parallel.** 10 threads claim 10
  different rows simultaneously. All succeed, no row left in `pending`.
- **Backoff serialization.** A worker fails a row with
  `next_eligible_at = now + 60s`. Another worker queries the dispatch
  index immediately. The failed row is not returned. After 60s, it is.

### Pool behavior tests

- **Pool respects size limits.** With pool size 3, never more than 3
  concurrent in-flight HTTP calls (mock the adapter to record
  concurrency, assert max).
- **Per-provider isolation.** twitterapi.io being slow does not block
  getxapi workers.
- **Graceful shutdown.** SIGTERM mid-fetch leaves the in-flight rows
  in `fetching` status. Next run re-claims them (the dispatch query
  includes `fetching` rows older than a stale threshold — see §9).

### Outcome tests

- **`reached_floor=True` → `complete`.** Mock adapter returns
  `FetchResult(..., reached_floor=True)`. Worker writes
  `status='complete'`.
- **`reached_floor=False` → `exhausted`.** Same as above with
  `reached_floor=False`.
- **HTTP 429 → `failed` with rate_limit class and next_eligible_at.**
  Mock adapter raises rate-limit exception. Worker writes
  `status='failed'`, `error_class='rate_limit'`,
  `next_eligible_at = now + 60s`.
- **Partial tweets land on rate-limit failure.** Mock adapter writes
  20 tweets then raises 429. Worker commits the 20, marks `failed`.
  Next claim re-runs, re-fetches; `INSERT OR IGNORE` absorbs the
  overlap.
- **Permanent failure does not retry.** Mock adapter raises auth
  exception. Worker writes `status='failed'`, `attempts = MAX_ATTEMPTS`.
- **`tweets_fetched` vs `tweets_written` diverge correctly.** Mock
  adapter returns 50 tweets, 30 already in DB. Ledger row shows
  `tweets_fetched=50`, `tweets_written=20`.

### Reconciliation tests

- **Both providers `complete`, counts agree → `ok`.**
- **Both providers `complete`, counts disagree → `mismatch`.**
- **One provider `complete`, other `failed` → reconciliation skipped,
  failed retries first.**

### Regression tests

- All existing tests still pass (the audit's 1 "works" verdict, B6,
  must not regress).
- The sequential `--sequential` fallback path produces identical
  results to the pool for a small fixture.

## 9. Stale `fetching` rows

A worker that crashes mid-fetch leaves a row in `fetching` status.
The dispatch query must reclaim such rows after a staleness threshold.

Implementation: dispatch query treats `fetching` rows older than 10
minutes as eligible for re-claim. The new claim is atomic (same
`BEGIN IMMEDIATE` protocol), increments `attempts`, and re-runs.

```sql
WHERE status IN ('pending', 'failed')
   OR (status = 'fetching' AND last_attempted_at < ?)   -- 10 min ago
```

10 minutes is a placeholder. Should exceed the longest plausible
fetch duration. Adjust if real-world fetches take longer.

## 10. Verification before declaring done

1. All new tests pass; all pre-existing tests pass.
2. WAL is verifiably enabled (`PRAGMA journal_mode` returns `wal`).
3. On a copy of production `data/fintwit.db`, run a single-day
   backfill for one handle via the pool. Confirm:
   - Ledger row transitions `pending` → `fetching` → `complete` (or
     `exhausted`).
   - `tweets_fetched` and `tweets_written` are populated.
   - `tweet_provenance` and `raw_tweets` are populated.
   - `error_class` is NULL on success.
4. Force a failure (mock 429): confirm `status='failed'`,
   `error_class='rate_limit'`, `next_eligible_at` set, partial tweets
   committed.
5. Run a 5-handle × 7-day backfill end-to-end. Confirm pool size
   limits hold (log inspection), total wall time roughly matches
   theoretical (workers × rate-limit interval).
6. Run the reconciliation step. Confirm `ok`/`mismatch` semantics
   match the pre-pool behavior on a fixture.
7. Confirm `git status` shows only the files in §5. No accidental
   writes to `snapshots.db`, no changes under `src/casino_dashboard/`
   or `src/ticker_digest/`.

## 11. Decision log

| Decision | Choice | Rationale |
|---|---|---|
| Worker pool: in-process threads | Yes | Workload size justifies; no external broker needed |
| Worker pool: per-provider sizing | Yes (5/3) | Independent rate budgets; one slow provider doesn't starve the other |
| Concurrency primitive | `ThreadPoolExecutor` | Stdlib, no async migration cost |
| Claim atomicity | `BEGIN IMMEDIATE` + conditional UPDATE | SQLite's native mechanism; no double-claim possible |
| Backoff schedule | Linear (60s/5m/30m) | Debuggable; exponential offers no measurable benefit at this scale |
| Max attempts | 3 | Beyond 3 you're not retrying, you're praying |
| Tweet count semantics | Split into fetched + written | Both metrics are useful; the cost is one column |
| `reached_floor` consumption | Worker reads, writes `complete`/`exhausted` | Closes the silent-truncation regression vector |
| Rate-limited partial behavior | Mark `failed`, not `ok` | Eliminates silent data loss; B7 fix |
| WAL transition | Pre-PR, separate commit | Isolates SQLite-mode change from concurrency change |
| Cross-process worker pool | No | YAGNI — single-process is plenty at 40 handles |
| Variance probe migration | No | Out of scope; variance inherits the schema changes for free |

---

*End of spec v1.0.*
