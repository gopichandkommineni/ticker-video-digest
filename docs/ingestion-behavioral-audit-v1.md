# Data Ingestion Layer — Behavioral Audit v1

Scenario under audit: *a user adds a new handle today and requests 180 days
of backfill.* For each of seven behaviors, the actual code path is traced
from entry point to outcome and given a single-value verdict.

## Summary table

| # | Behavior | Verdict | Notes |
|---|----------|---------|-------|
| B1 | Request division | works | Window is sliced into per-(handle, date, provider) rows; even finer than required. |
| B2 | Ledger population | partial | `pending` written before, `ok`/`mismatch`/`failed` after. No DURING update; `fetching`/`complete`/`exhausted` never written to `day_fetch_log`. |
| B3 | Worker pool creation | not-implemented | `run_days` is a sequential `for` loop with `time.sleep`. No concurrency primitive anywhere. |
| B4 | Ledger concurrency safety | not-implemented (not exercised) | No row-claiming; `mark_day` uses a deferred transaction. Live DB is `journal_mode=delete`, not WAL. Moot until B3 exists. |
| B5 | Pagination correctness | partial | Page cap is 1000 and `FetchResult.reached_floor` is returned, but no caller reads it — `complete`/`exhausted` are never set. |
| B6 | Raw tweet write correctness | works | `INSERT OR IGNORE` on `tweet_id`; `first_seen_at`/`last_seen_at` set; one `tweet_provenance` row per (tweet_id, provider). |
| B7 | Ledger outcome accuracy | partial | `tweet_count` is fetched-count, not rows-written; `error_class` never set; rate-limited partial fetches are committed and marked `ok`. |

## Methodology

Read in full: `orchestration/runner.py`, `orchestration/day_fetcher.py`,
`storage/day_log.py`, `storage/tweets.py`, `storage/db.py`,
`tweet_sources/base.py`, `tweet_sources/twitterapi.py`,
`tweet_sources/getxapi.py`, `scripts/run_backfill.py`,
`scripts/run_daily.py`. Grepped the ingestion tree for concurrency
primitives, `day_fetch_log` writers, `reached_floor` usages, and
`error_class` writers. One dynamic check ran against the live
`data/fintwit.db` using an `immutable=1` read-only URI: `PRAGMA
journal_mode`, `PRAGMA table_info(day_fetch_log)`, and `SELECT DISTINCT
status FROM day_fetch_log` (read-only, no sidecar files created). NOT
checked: `tweet_sources/_http.py` retry internals beyond their public
exception types, the GitHub Actions workflow YAML, and any live row
contents beyond the distinct-status set.

## Per-behavior findings

### B1. Request division

**Verdict:** works

**Trace:**
- Entry point: `orchestration/runner.py:136` (`backfill_handle(handle, floor, now.date())`)
- Key call: `orchestration/day_fetcher.py:281` → `storage/day_log.py:21` (`populate_pending_days`)
- Outcome: `storage/day_log.py:44-50` (one INSERT per (handle, date, provider))

**Code excerpt:**

```python
# storage/day_log.py:32-50
rows: list[tuple] = []
day = since
while day <= until:
    for provider in providers:
        rows.append((handle, day.isoformat(), provider))
    day += datetime.timedelta(days=1)
...
    INSERT OR IGNORE INTO day_fetch_log (handle, date, provider, status)
    VALUES (?, ?, ?, 'pending')
```

**Evidence:** The window `[since, until]` is decomposed one calendar day at
a time, and for each day one row per provider is created. The provider is
*not* handed a range to slice internally — it is called once per single day
(`day_fetcher.py:130`, `src.fetch_tweets(handle, day, day)`). The unit of
work is therefore (handle, date, provider), finer than the (handle, date)
the rubric asks for. For 180 days × 2 providers that is 360 ledger rows.

**Gap (if any):** No gap.

### B2. Ledger population

**Verdict:** partial

**Trace:**
- Before: `storage/day_log.py:46` (`INSERT OR IGNORE ... 'pending'`)
- After: `storage/day_log.py:147-165` (`mark_day` UPDATE) called from `day_fetcher.py:133, 151, 181, 206`
- During: none

**Code excerpt:**

```python
# storage/day_log.py:149-156 (mark_day — the only UPDATE path)
UPDATE day_fetch_log
SET status      = ?,
    tweet_count = COALESCE(?, tweet_count),
    fetched_at  = ?,
    error       = COALESCE(?, error),
    retry_count = retry_count + ?
WHERE handle = ? AND date = ? AND provider = ?
```

**Evidence:** Rows are created `pending` before any fetch
(`populate_pending_days`) and finalized to `ok`, `mismatch`, or `failed`
after the fetch by `mark_day`. There is no DURING transition: a row stays
`pending` while its day is being fetched, then jumps straight to a terminal
status. The Step 2 schema introduced `fetching`, `complete`, and
`exhausted` (`storage/db.py:15-18`), but grep finds no code writing any of
them to `day_fetch_log` — the only `"fetching"` literal is a `handles.status`
value (`runner.py:117`), a different table. The live DB confirms this: `SELECT
DISTINCT status FROM day_fetch_log` returns only `ok` and `mismatch`.

**Gap (if any):** No DURING/claim status on `day_fetch_log`; three of the
seven defined statuses (`fetching`, `complete`, `exhausted`) are dead schema.

### B3. Worker pool creation

**Verdict:** not-implemented

**Trace:**
- Entry point: `orchestration/day_fetcher.py:217` (`run_days`)
- Key call: `orchestration/day_fetcher.py:235-247` (the loop)
- Outcome: serial execution with inter-day sleep

**Code excerpt:**

```python
# orchestration/day_fetcher.py:235-247
for date_str in sorted(dates):
    ...
    for provider in PROVIDERS:
        if provider not in providers_needed:
            continue
        count, err = _fetch_one_day(handle, date_str, provider, db_path, inter_day_delay)
        ...
    day_status = _verify_and_mark(handle, date_str, counts, errors, db_path)
```

**Evidence:** Both backfill and daily paths funnel into `run_days`, which is
a plain nested `for` loop — outer over dates, inner over providers — with a
`time.sleep(inter_day_delay)` (default 1 s) inside `_fetch_one_day`
(`day_fetcher.py:158`). A grep of `orchestration/`, `storage/`,
`tweet_sources/`, and `scripts/` for `ThreadPoolExecutor`,
`concurrent.futures`, `asyncio`, `Semaphore`, `threading`, and
`multiprocessing` returns nothing. A 180-day backfill runs 360 sequential
provider calls.

**Gap (if any):** No bounded worker pool and no per-provider concurrency
limit exist; ingestion is strictly sequential.

### B4. Ledger concurrency safety

**Verdict:** not-implemented (not exercised — see B3)

**Trace:**
- Writer: `storage/day_log.py:144-167` (`mark_day`)
- Transaction: `with conn:` (BEGIN DEFERRED)
- Pragma: `storage/db.py:148` sets WAL per-connection; live DB header reports `delete`

**Code excerpt:**

```python
# storage/day_log.py:144-165
conn = get_connection(db_path)
try:
    with conn:                       # deferred transaction, not IMMEDIATE/EXCLUSIVE
        conn.execute(
            "UPDATE day_fetch_log SET status = ? ... WHERE handle = ? AND date = ? AND provider = ?",
            ...,
        )
finally:
    conn.close()
```

**Evidence:** `mark_day` opens a deferred transaction (`with conn:`) and does
a blind `UPDATE` keyed on the primary key. There is no `SELECT ... then
claim` pattern, no `BEGIN IMMEDIATE`/`BEGIN EXCLUSIVE`, and no
`next_eligible_at`-based dispatch claim — so nothing prevents two workers
from selecting the same `pending` row and both fetching it. This is harmless
today only because B3 is sequential. Note also that `get_connection`
(`db.py:148`) issues `PRAGMA journal_mode=WAL` per connection, but the live
`data/fintwit.db` reports `journal_mode=delete` — WAL is not persisted on the
committed database, so concurrent readers/writers would serialize on the
file lock.

**Gap (if any):** No atomic row-claim and no persisted WAL; both must land
before parallel workers can touch the ledger safely.

### B5. Pagination correctness

**Verdict:** partial

**Trace:**
- Loop: `tweet_sources/twitterapi.py:84-137` (and identical `getxapi.py:87-137`)
- Cap: `_MAX_PAGES = 1000` (`twitterapi.py:19`, `getxapi.py:19`)
- Flag returned: `FetchResult(tweets=..., reached_floor=...)` (`twitterapi.py:149`)
- Flag consumed: nowhere

**Code excerpt:**

```python
# tweet_sources/twitterapi.py:139-149
if not reached_floor:
    logger.warning(
        "twitterapi.io: hit page cap (%d) before reaching floor %s for %s — backfill incomplete",
        _MAX_PAGES, start, handle,
    )
...
return FetchResult(tweets=tweets, reached_floor=reached_floor, skipped=skipped)
```

**Evidence:** Both adapters paginate via cursor until an empty batch, a tweet
older than `start`, or a missing `next_cursor` — the natural-stop cases all
set `reached_floor=True`. The cap is confirmed at 1000 (the prior `100`-bug
fix), and `FetchResult` carries `reached_floor`. But the completeness flag is
discarded: a grep for `reached_floor` in `orchestration/` and `storage/`
finds only docstrings stating it "is never read." `_fetch_one_day`
(`day_fetcher.py:130`) ignores it entirely, so a cap-truncated day is marked
`ok`/`mismatch` purely on cross-provider count agreement. The `complete` vs
`exhausted` statuses that should encode this distinction are never written
(see B2).

**Gap (if any):** A page-capped (truncated) window returns
`reached_floor=False` but is still finalized as `ok`, because no caller maps
the flag to `exhausted`.

### B6. Raw tweet write correctness

**Verdict:** works

**Trace:**
- Entry point: `orchestration/day_fetcher.py:143` (`upsert_tweets(rows)`)
- Key call: `storage/tweets.py:59-92` (INSERT OR IGNORE + conditional last_seen_at refresh)
- Provenance: `storage/tweets.py:148-171` (`_record_provenance`)

**Code excerpt:**

```python
# storage/tweets.py:85-94
if cur.rowcount == 1:
    inserted += 1
else:
    # Already present — refresh last_seen_at, preserve first_seen_at.
    conn.execute(
        "UPDATE raw_tweets SET last_seen_at = ? WHERE tweet_id = ?",
        (now, params["tweet_id"]),
    )
_record_provenance(conn, params["tweet_id"], params["source_provider"], now)
```

**Evidence:** Writes are idempotent via `INSERT OR IGNORE` on the `tweet_id`
primary key. `first_seen_at` and `last_seen_at` are both set on first insert
(`tweets.py:56-58`); on a re-fetch only `last_seen_at` is refreshed,
preserving `first_seen_at`. Every observation upserts a `tweet_provenance`
row keyed on (tweet_id, provider) with `ON CONFLICT ... DO UPDATE
last_seen_at`. `raw_json` is populated unconditionally from
`t.raw_provider_json`; the variance-probe case where that is `None` is not
specially branched — the row is still written with a NULL `raw_json`, which
is valid (the column is nullable), so probe and live-ingest paths share one
write path without divergence.

**Gap (if any):** No gap. (Provenance is skipped only when `source_provider`
is falsy — `tweets.py:161-162` — which does not occur on the live ingest
path where the provider is always set.)

### B7. Ledger outcome accuracy

**Verdict:** partial

**Trace:**
- Success path: `day_fetcher.py:140-159` then `_verify_and_mark` → `mark_day`
- Exception path: `day_fetcher.py:131-138` (`mark_day(... status="failed", tweet_count=0 ...)`)
- `error_class`: declared `db.py:184`, never written

**Code excerpt:**

```python
# orchestration/day_fetcher.py:140-159
if result.tweets:
    rows = _to_storage_rows(result.tweets, handle, provider)
    try:
        upsert_result = upsert_tweets(rows, db_path=db_path)   # dedups; inserted may be < len
    except Exception as exc:
        mark_day(handle, date_str, provider, status="failed",
                 tweet_count=len(result.tweets), error=str(exc), ...)
        return len(result.tweets), str(exc)
time.sleep(inter_day_delay)
return len(result.tweets), None        # returns FETCHED count, not inserted
```

**Evidence:** `tweet_count` recorded in `day_fetch_log` is
`len(result.tweets)` — the provider's returned count — not
`upsert_result.inserted`, the rows actually new to `raw_tweets`. Because
`upsert_tweets` dedups across providers and re-runs, the ledger count
overcounts net-new rows. `error_class` exists in the schema but `mark_day`
only writes the free-text `error` column, never `error_class`. On a
mid-pagination failure the behavior splits: if `fetch_tweets` *raises*, the
adapter has accumulated tweets in memory and never returned them, so nothing
is written for that provider and the row is marked `failed` with
`tweet_count=0` — clean, no half-state. But if pagination is cut short by an
exhausted retry budget, the adapter *catches* it, keeps the partial tweets,
and returns `reached_floor=False` (`twitterapi.py:97-103`); those partial
tweets are upserted and the day is then marked `ok`/`mismatch` by count
agreement — a truncated fetch is silently committed as a success.

**Gap (if any):** `tweet_count` ≠ rows written, `error_class` is never
populated, and rate-limit-truncated partial fetches are recorded as `ok`.

## Cross-cutting observations

- B2, B5, and B7 share one root cause: `reached_floor` / `complete` /
  `exhausted` are plumbed into the schema and the `FetchResult` but no caller
  consumes them. Completeness is decided solely by cross-provider count
  agreement, so truncation is invisible.
- B2 and B7 both flow through the single `mark_day` write path; its choice to
  store fetched-count and to ignore `error_class` affects both verdicts at
  once.
- B3 (no worker pool) makes B4 moot in practice — the ledger races it does not
  guard against cannot occur while execution is sequential.
- The Step 2 migration is purely additive (columns + statuses + a dispatch
  index, `db.py:181-199`); none of the new columns (`next_eligible_at`,
  `error_class`, `reached_floor`, `first_attempted_at`, `last_succeeded_at`)
  are read or written by current ingestion code.
- The live DB is `journal_mode=delete` despite the per-connection WAL pragma,
  so the on-disk database is not configured for the concurrent access the
  worker pool will need.

## Worker-pool readiness

The worker-pool work is an **extension** of the existing system, not a
replacement. The decomposition that a pool needs already exists and works:
`populate_pending_days` materializes per-(handle, date, provider) `pending`
rows up front (B1), and `get_pending_days` / `get_retryable_days` already
return work-queue slices — a pool would consume the same queue the
sequential `run_days` loop consumes today. What is missing is bounded and
additive: a concurrency primitive around the existing per-day call (B3), an
atomic claim transition (`pending` → `fetching`) with `BEGIN IMMEDIATE` plus
`next_eligible_at` so two workers cannot double-claim (B4), persisted WAL on
the database file (B4), and consumption of the already-returned
`reached_floor` flag to set `complete` vs `exhausted` (B5). None of these
require rewriting the fetch, verify, or upsert logic — the schema columns and
status vocabulary are already in place and merely unused. The honest summary:
the data model is ready, the execution model is not, and the gap is filling
in code paths the schema already anticipates.
