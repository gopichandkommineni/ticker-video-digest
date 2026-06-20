# Ingestion Ledger Gaps — v1

**Project:** ticker-video-digest / FinTwit ingestion
**Date drafted:** 2026-06-20
**Status:** Spec for review. Not yet implemented.
**Owner:** AG

---

## 1. Context

The FinTwit ingestion pipeline (`tweet_sources/` + `orchestration/` +
`storage/`, writing to `data/fintwit.db`) has been shipping data for
months. As of the most recent audit it holds 26,687 tweets across 9
handles, with 1,512 (handle, date) fetch records — each logged twice,
once per provider (twitterapi.io and getxapi).

The existing `day_fetch_log` table is **a post-hoc reconciliation log,
not a retry ledger.** Its `status` field carries only `ok` (3,020 rows)
or `mismatch` (4 rows). There is no `pending` state waiting for a
worker; no `failed` state after retries; no representation of "this
job needs to be tried again later with backoff." Whatever retry logic
exists today lives in code, not in the table.

This spec **adds retry-ledger semantics on top of the existing
reconciliation log**, without breaking the reconciliation behavior.
The motivation is to prevent the silent-failure class previously
documented in `docs/project-context-v2.md`: the system has historically
lost data to silent truncation (the `_MAX_PAGES=100` bug), and the
audit confirmed that while truncation isn't currently happening in
the data (max observed = 126 tweets/day against a 20,000 theoretical
ceiling), the table has no mechanism to *prevent regression* if
truncation begins occurring at higher scale.

This spec is **additive only.** No existing column is dropped or
renamed. No existing row is modified. The current fetcher's behavior
is unchanged. Only new tables, new columns, and new write paths are
introduced.

## 2. Decisions locked by the data audit

The audit (`/tmp/fintwit_data_audit.md`) surfaced five facts that
shape this spec:

1. **Status vocabulary is `ok`/`mismatch`.** We add new status values
   (`pending`, `failed`, `exhausted`) alongside, not in place. The
   existing values keep working.
2. **`raw_json` is 100% NULL in current data.** Going forward, the
   column will be populated by both adapters at ingest. Historical
   rows stay NULL — they were ingested under the old regime.
3. **Both providers write into `raw_tweets` with `source_provider`
   reflecting whichever insert won the race.** A new
   `tweet_provenance` join table replaces single-column attribution.
   `source_provider` on `raw_tweets` is kept for backwards
   compatibility but deprecated in queries.
4. **`mismatch` rows are cross-provider count disagreements, not
   fetch failures.** This signal is currently surfaced but not
   tracked. A new `mismatch_resolutions` table tracks investigation
   outcomes per (handle, date).
5. **No truncation has occurred and denormalization is clean.**
   No reconciliation pass is needed for existing data. The
   `reached_floor` distinction is preventive, not reactive.

## 3. Schema changes

All changes are **additive.** SQLite migrations use `ALTER TABLE ADD
COLUMN` (idempotent if guarded by a `PRAGMA table_info` check) and
`CREATE TABLE IF NOT EXISTS`.

### 3.1 `day_fetch_log` — new columns

```sql
ALTER TABLE day_fetch_log ADD COLUMN next_eligible_at     TEXT;
ALTER TABLE day_fetch_log ADD COLUMN error_class          TEXT;
ALTER TABLE day_fetch_log ADD COLUMN reached_floor        INTEGER;
ALTER TABLE day_fetch_log ADD COLUMN first_attempted_at   TEXT;
ALTER TABLE day_fetch_log ADD COLUMN last_succeeded_at    TEXT;
```

Column semantics:

- **`next_eligible_at`** — ISO-8601 UTC timestamp. NULL means
  eligible immediately. Set after a transient failure (e.g. 429)
  to defer the next retry. Workers' dispatch query filters by
  `next_eligible_at IS NULL OR next_eligible_at <= now()`.
- **`error_class`** — small enum: `rate_limit`, `auth`, `timeout`,
  `network`, `parse`, `unknown`. Separated from `error` (free-text
  detail) so failures can be aggregated by class without parsing
  strings.
- **`reached_floor`** — 0/1 boolean. 1 means the provider explicitly
  signaled "no more pages for this window." 0 means we stopped for
  another reason (page cap, error). NULL on existing rows.
- **`first_attempted_at`** / **`last_succeeded_at`** — debugging
  timestamps. NULL on existing rows.

### 3.2 `day_fetch_log` — extended status vocabulary

Status values supported (existing values keep working):

| Status | Meaning | Set by |
|---|---|---|
| `ok` | Both providers fetched, counts agree | existing reconciliation |
| `mismatch` | Both providers fetched, counts disagree | existing reconciliation |
| `pending` | Eligible for fetch, never attempted | new planner |
| `fetching` | Claimed by a worker, in flight | new worker |
| `complete` | Single-provider fetch, provider confirmed end-of-window (`reached_floor=1`) | new worker |
| `exhausted` | Single-provider fetch, stopped at page cap (`reached_floor=0`) | new worker |
| `failed` | Max retries exceeded | new worker |

`ok` and `mismatch` are reconciliation outcomes (terminal, two-provider
view). `complete`, `exhausted`, `failed` are single-provider fetch
outcomes. A `(handle, date, provider)` row moves through `pending` →
`fetching` → (`complete` | `exhausted` | `failed`). Reconciliation may
later overwrite the status to `ok`/`mismatch` if and only if both
provider rows reached a terminal state.

### 3.3 New index for the dispatch query

```sql
CREATE INDEX IF NOT EXISTS idx_day_fetch_log_dispatch
  ON day_fetch_log (status, next_eligible_at)
  WHERE status IN ('pending', 'failed');
```

Partial index keeps it tiny — only eligible-to-dispatch rows. Hot
path for the worker pool.

### 3.4 New table: `tweet_provenance`

```sql
CREATE TABLE IF NOT EXISTS tweet_provenance (
    tweet_id        TEXT NOT NULL,
    provider        TEXT NOT NULL,    -- 'twitterapi' | 'getxapi'
    first_seen_at   TEXT NOT NULL,    -- when this provider first returned it
    last_seen_at    TEXT NOT NULL,    -- most recent fetch that returned it
    PRIMARY KEY (tweet_id, provider)
);

CREATE INDEX IF NOT EXISTS idx_tweet_provenance_provider
  ON tweet_provenance (provider, last_seen_at DESC);
```

Replaces the single `source_provider` column on `raw_tweets` for
provenance queries. Supports questions like:

- "Which tweets did getxapi return that twitterapi didn't?"
- "Has provider X stopped returning tweets we used to see?"
- "When did we first see tweet T from each provider?"

`raw_tweets.source_provider` stays for backwards compatibility but is
no longer authoritative — code reading provenance should use
`tweet_provenance`.

### 3.5 New table: `tweet_labels`

```sql
CREATE TABLE IF NOT EXISTS tweet_labels (
    tweet_id              TEXT NOT NULL,
    label_type            TEXT NOT NULL,   -- 'ticker' | 'useful' | 'sentiment' | ...
    label_value           TEXT NOT NULL,   -- e.g. 'RKLB' for ticker
    classifier_version    TEXT NOT NULL,   -- e.g. 'regex-v1', 'llm-v2'
    confidence            REAL,            -- 0.0-1.0, NULL if not applicable
    labeled_at            TEXT NOT NULL,
    PRIMARY KEY (tweet_id, label_type, label_value, classifier_version)
);

CREATE INDEX IF NOT EXISTS idx_tweet_labels_ticker
  ON tweet_labels (label_value, label_type)
  WHERE label_type = 'ticker';

CREATE INDEX IF NOT EXISTS idx_tweet_labels_tweet
  ON tweet_labels (tweet_id, label_type);
```

Holds all derived labels separately from raw data. Replayable: change
the classifier, re-run, new rows get inserted under the new
`classifier_version`. Old labels stay queryable.

Initial expected use: ticker extraction (regex on cashtags
`\$[A-Z]{1,5}\b`). Future uses: usefulness filter, sentiment, thesis
classification. Schema is generic enough to support all of them.

This table is **created but not populated** in this PR. The v1 ticker
extractor is a separate, smaller PR. The schema is locked here so the
extractor can be designed against it.

### 3.6 New table: `mismatch_resolutions`

```sql
CREATE TABLE IF NOT EXISTS mismatch_resolutions (
    handle              TEXT NOT NULL,
    date                TEXT NOT NULL,
    getxapi_count       INTEGER,
    twitterapi_count    INTEGER,
    resolution          TEXT NOT NULL,    -- 'unresolved' | 'truncation' | 'deletion' |
                                          -- 'provider_index_stale' | 'data_corruption' |
                                          -- 'accepted_drift'
    note                TEXT,             -- free-text from human investigator
    resolved_at         TEXT,             -- NULL while unresolved
    PRIMARY KEY (handle, date)
);
```

One row per (handle, date) that ever had `status='mismatch'`. The 4
existing mismatch rows from the audit get inserted with
`resolution='unresolved'` and `resolved_at=NULL` as part of the
migration. Future mismatches get auto-inserted by the reconciliation
step.

Investigation can be manual (CLI command to set resolution) or
deferred indefinitely. The table's value is *making non-investigation
visible* — without it, mismatches accumulate silently.

### 3.7 `raw_tweets` — new columns

```sql
ALTER TABLE raw_tweets ADD COLUMN first_seen_at  TEXT;
ALTER TABLE raw_tweets ADD COLUMN last_seen_at   TEXT;
```

Semantics:

- **`first_seen_at`** — set on INSERT, never updated. NULL for
  existing 26,687 historical rows.
- **`last_seen_at`** — set on INSERT and refreshed on every subsequent
  upsert. NULL for existing rows; populated on next re-fetch.

The existing `fetched_at` column stays as-is. New code reads
`first_seen_at` / `last_seen_at`; legacy code reading `fetched_at`
keeps working.

### 3.8 `raw_tweets.raw_json` — start populating

No schema change. The column exists and is currently 100% NULL.
Both adapters (`tweet_sources/twitterapi.py`,
`tweet_sources/getxapi.py`) are updated to pass through the raw
provider JSON for each tweet at ingest. Existing rows stay NULL.

Size cap: 50 KB per row. If a provider response exceeds the cap, the
JSON is truncated and a log warning is emitted. This prevents one
pathological tweet (e.g. a status with hundreds of media items) from
silently bloating the table.

## 4. Backfill rules for existing data

For each new column, the rule for the 26,687 existing rows:

| Table | Column | Backfill rule |
|---|---|---|
| `day_fetch_log` | `next_eligible_at` | NULL (interpreted as eligible immediately) |
| `day_fetch_log` | `error_class` | NULL for existing `ok`/`mismatch` rows (no error) |
| `day_fetch_log` | `reached_floor` | NULL (unknown for historical rows) |
| `day_fetch_log` | `first_attempted_at` | NULL (historical, not tracked at the time) |
| `day_fetch_log` | `last_succeeded_at` | Copy from existing `fetched_at` for `status='ok'` rows; NULL otherwise |
| `raw_tweets` | `first_seen_at` | NULL (Q3 decision: honest absence beats lying proxy) |
| `raw_tweets` | `last_seen_at` | NULL |
| `mismatch_resolutions` | (new rows) | Insert one row for each existing `day_fetch_log` row where `status='mismatch'` (4 rows expected), with `resolution='unresolved'` |

The one-time migration script lives at
`scripts/migrate_ingestion_ledger_v1.py`. It is idempotent: running
twice should produce the same end state.

## 5. Out of scope — DO NOT BUILD in this PR

- **Worker pool implementation.** The schema supports it (the
  dispatch query in §3.3 is ready), but the actual `ThreadPoolExecutor`
  + per-provider rate limiter + planner loop is a separate PR. This
  PR establishes the *data layer* for the new system; the *execution
  layer* comes next.
- **Ticker extraction.** `tweet_labels` is created but empty. The v1
  regex extractor (`\$[A-Z]{1,5}\b`) ships in its own PR with its own
  tests.
- **Mismatch resolution UI/CLI.** The `mismatch_resolutions` table is
  created and seeded with 4 existing mismatches as `unresolved`. The
  command to update a resolution (whether CLI flag, Streamlit page,
  or YAML loader) is deferred.
- **Migrating historical `source_provider` to `tweet_provenance`.**
  The single-column attribution on existing rows is irrecoverable
  (it reflects insert-race winners, not real provenance). Historical
  rows do not get migrated. Going forward, both adapters write to
  `tweet_provenance` at ingest.
- **`raw_json` backfill for historical rows.** Existing 26,687 rows
  stay NULL. Re-fetching them to populate `raw_json` is API-expensive
  and provides limited value.
- **WAL mode on `snapshots.db`.** Separate concern, separate PR. This
  spec only touches `fintwit.db`, which is already on WAL.
- **Any change to `tweet_sources/`, `orchestration/`, `storage/`
  Python code** beyond the minimal updates needed to write to the new
  columns/tables at ingest.
- **Any change to `casino_dashboard/` or `ticker_digest/`.** This PR
  is contained to `storage/` (schema + migration), `tweet_sources/`
  (raw_json passthrough), and the migration script.

## 6. Tests required

- **Schema migration idempotency.** Running the migration script
  twice yields identical schema and identical row counts.
- **Existing row preservation.** Pre-migration row counts for
  `raw_tweets`, `day_fetch_log`, `handles` must match post-migration
  exactly.
- **Existing column preservation.** Every pre-migration value in
  `raw_tweets.tweet_id`, `text`, `created_at_utc`, `source_provider`
  is identical post-migration. (Sample 100 rows, full equality check.)
- **New column defaults.** `next_eligible_at`, `reached_floor`,
  `first_seen_at`, `last_seen_at` are NULL for existing rows.
- **`mismatch_resolutions` seeded.** Exactly 4 rows post-migration,
  all with `resolution='unresolved'`.
- **`tweet_provenance` table exists and is empty.** No backfill of
  historical provenance.
- **`tweet_labels` table exists and is empty.** No labels in this PR.
- **Adapter changes.** Mock `twitterapi.io` and `getxapi` responses,
  assert that ingest now writes (a) `raw_json` to `raw_tweets`,
  (b) `first_seen_at` and `last_seen_at` on `raw_tweets`,
  (c) a row to `tweet_provenance` for each (tweet_id, provider) pair.
- **Size cap.** A mocked response with `raw_json > 50 KB` is truncated
  and a warning is logged.
- **Backwards compatibility.** Existing `tweet_sources/compare.py`
  and `storage/reads.py` queries continue to work without
  modification.

## 7. Verification before declaring done

1. All new tests pass.
2. All pre-existing tests still pass.
3. Run the migration script against a copy of `data/fintwit.db`.
   Diff the pre-and-post schemas — only the additive changes from §3
   should appear.
4. Run a single fetch via the existing CLI
   (`python -m tweet_sources <provider> <handle>` or the equivalent
   orchestration entry point). Confirm a new row in `raw_tweets`
   carries: non-NULL `raw_json`, non-NULL `first_seen_at`, non-NULL
   `last_seen_at`. Confirm a new row in `tweet_provenance` for
   the (tweet_id, provider) pair.
5. Confirm `git status` shows only the intended file changes — no
   `.db-shm` / `.db-wal` sidecars committed.
6. Confirm `data/fintwit.db` is in a state that the existing daily
   workflow (`.github/workflows/fintwit-daily.yml`) can still write
   to without error.

## 8. Decision log

| Decision | Choice | Rationale |
|---|---|---|
| Populate `raw_json` going forward | Yes | Replayability: re-parsing without re-fetching |
| Drop `raw_json` column | No | Keep for new ingests; size-cap mitigates blob risk |
| Promote `mismatch` to tracked outcome | Yes | Future-proofs investigation, prevents silent accumulation |
| Backfill historical `first_seen_at` from `fetched_at` | No | Proxy data that looks real but lies is worse than honest NULL |
| Backfill historical `source_provider` to `tweet_provenance` | No | Existing values are insert-race winners, not real provenance — irrecoverable |
| Reclassify existing `complete` rows as `exhausted` | No | Audit found no truncation — no rows need reclassification |
| Add `next_eligible_at` for backoff | Yes | Required for fair retry without starvation |
| Promote status enum from 2 values to 7 | Yes | New states added alongside existing — backward compatible |
| Build worker pool in this PR | No | Out of scope: this PR is data layer only |
| Build ticker extractor in this PR | No | Out of scope: schema locked, extractor is separate PR |

---

*End of spec v1.0.*
