# PR B (revised) — production cutover to the worker pool, via `ingest_handle`

## 0. Why the original plan didn't work (one line)
Production runs `run_daily.py → ingest_all → ingest_handle → delta/backfill_handle
→ day_fetcher.run_days` (sequential). `runner.run_days` (the pool) is unreachable
from production. The cutover must change `ingest_handle`'s fetch mechanism, not a
`run_days` default. See `/tmp/pr_b_cutover_corrected_spec.md`.

## 1. Design overview
Flip `ingest_handle` to dispatch its fetch through the pool, keeping everything
else (window logic, handle-status lifecycle, `RunResult`, exit codes) intact.
Scripts and workflows are **unchanged** — that's the win of doing it at the
`ingest_handle` layer.

Two structural wrinkles drive the design:

- **`run_pool`/`get_eligible_jobs` are global-dispatch** — the dispatch query has
  no handle/date filter, so a per-handle pool run would drain *every* handle's
  eligible rows. Fix: add an **optional `handles` filter** to `get_eligible_jobs`
  (threaded through `run_pool`), default `None` = today's global behavior.
- **The dispatch query never re-claims `mismatch` rows** (only
  `pending`/`failed`/stale-`fetching`). Delta today retries `mismatch` via
  `get_retryable_days`. Fix: **re-open** outstanding `mismatch` rows to `pending`
  before the pool run (`failed` rows are already eligible, so no action needed
  for them).

## 2. Concrete changes

### 2a. `storage/day_log.py`
- `get_eligible_jobs(conn, limit, now, *, max_attempts, stale_threshold_sec,
  handles=None)`: when `handles` is provided, append `AND handle IN (...)` to the
  WHERE. Default `None` → unchanged (existing tests unaffected).
- New `reopen_mismatch_days(conn, handle, max_attempts) -> int`: 
  `UPDATE day_fetch_log SET status='pending' WHERE handle=? AND status='mismatch'
  AND retry_count < ?`. Mirrors the `mismatch` arm of `get_retryable_days`.
  Returns rows re-opened. (Idempotent; respects the attempt cap so terminal
  mismatches stay put.)

### 2b. `orchestration/worker_pool.py`
- `run_pool(..., handles_filter=None)`: pass `handles=handles_filter` into the
  `get_eligible_jobs` call inside the dispatch loop. Default `None` → unchanged.
  (No change to the claim protocol, backoff, or outcome handling.)

### 2c. `orchestration/runner.py` — the actual cutover
- `ingest_handle(handle, ..., sequential: bool = False)`:
  - **Step 5 replaced.** Keep Steps 1–4 (status read, F4 skip, backfill-vs-delta
    decision, mark in-progress) and Step 6 (coverage_floor, outstanding,
    handle-status, RunResult) **verbatim** — Step 6 already reads the ledger via
    `day_summary`/`coverage_floor`, so it's agnostic to who wrote the rows.
  - New Step 5 (pool branch, the default):
    1. Compute the window exactly as today: delta → `(today-2, today)`; backfill →
       `(floor, today)`.
    2. `reopen_mismatch_days(conn, handle, max_attempts)` (delta only — backfill
       has no priors) so outstanding mismatches re-dispatch.
    3. `run_pool([handle], (since, until), config, db_path,
       handles_filter=[handle])` — scoped so only this handle's eligible rows
       (new window + reopened mismatch + old failed) are drained.
    4. `reconcile_completed_days(conn)` → ledger now carries `ok`/`mismatch`.
    5. Build the `summary` counts for `RunResult.days_*` from
       `day_summary(handle)` (or have run_pool/reconcile return per-handle counts).
  - `sequential=True` → the **existing** `delta_handle`/`backfill_handle` path,
    unchanged. This is the documented debug/rollback fallback (keeps
    `day_fetcher.run_days` alive).
  - Keep the `try/except` around the fetch → `RunResult(failed)` + handle status
    `failed`, identical to today.
- `ingest_all(..., sequential: bool = False)`: thread `sequential` into the
  per-handle `ingest_handle` calls. Still a loop of per-handle (scoped) pool runs
  — preserves per-handle `RunResult` attribution and the F4 skip. (Top-level
  handles run one at a time; each handle's days×providers run concurrently. A
  single batched all-handles pool is a possible follow-up optimization, noted but
  out of scope to keep risk low and attribution simple.)

### 2d. Scripts / workflows / variance — NO CHANGES
`run_daily.py`, `run_backfill.py`, `.github/workflows/*`, `run_variance.py` are
untouched. The default flips because `ingest_handle`/`ingest_all` now default to
the pool internally.

## 3. Mismatch-retry decision (the explicit call)
**Chosen: re-open `mismatch → pending` before the pool run** (§2a/§2c), scoped to
the handle, gated on `retry_count < max_attempts`. Rationale: localized, mirrors
`get_retryable_days` exactly, requires **no change to the dispatch query** (so no
risk of globally re-claiming every mismatch on unrelated runs), and reconciliation
re-issues the same `ok`/`mismatch` verdict. `failed` rows need no special handling
— the dispatch query already re-claims them once backoff elapses.

## 4. Behavior-parity notes (call out in the PR)
- `RunResult.days_ok/mismatch/failed` shift from "counts from this run's loop" to
  "ledger counts for the handle" (read via `day_summary`). Outcome
  (`ok`/`incomplete`/`failed`/`skipped`) and handle-status transitions are
  identical because Step 6 is unchanged.
- Within-run immediate retry differs: the sequential path does one inline retry
  pass; the pool defers transient failures to `next_eligible_at` and relies on the
  next scheduled Action (ledger-as-queue). This is the intended pool behavior
  (worker-pool spec §5.4), already shipped in #102/#103.
- Rollback: revert the merge → `ingest_handle` default returns to sequential. No
  table-shape change; both paths write the same tables.

## 5. Tests — `tests/test_pr_b_cutover.py`
- **ingest_handle parity:** same fixture/mock adapter, run `sequential=True` vs
  default(pool) on two fresh DBs → assert identical final `day_fetch_log` statuses
  per `(handle,date,provider)` and identical `RunResult.outcome` + handle status.
- **mismatch re-fetch:** seed a prior `mismatch` day, run delta via pool → assert
  the day was re-claimed, re-fetched, and re-verdicted (reopen works); seed a
  `mismatch` with `retry_count==max` → assert it is NOT reopened (terminal).
- **handle-scoping:** two handles each with an eligible `failed` day; run
  `ingest_handle(h1)` → assert only h1's row was claimed (h2 untouched), proving
  the `handles` filter.
- **ingest_all default routes to pool:** monkeypatch `run_pool`, call
  `ingest_all()` → assert `run_pool` invoked (and `ingest_all(sequential=True)`
  does not).
- **ingest_all isolation (regression of T7):** one handle's adapter raises → batch
  continues, that handle is `failed`.
- Full suite green minus the 15 known pre-existing failures; concurrency suite
  stable 6×.

## 6. Verification (dry-run on a BACKUP copy of data/fintwit.db)
- `python scripts/run_daily.py --help` unchanged for operators (it takes no args
  today; confirm still true).
- Run `ingest_all` (or `run_daily.py`) against a backup DB with a mock adapter for
  a small handle subset → pool engages (pool log lines), ledger transitions
  `pending→fetching→complete/exhausted→ok/mismatch`, no rows stuck in `fetching`.
- Run with `sequential=True` (or a `--sequential`-style override if added) →
  legacy loop, no pool log lines.
- `git status` clean: no `data/*.db`, no `src/`, no `.github/` changes.

## 7. Estimated diff
~60–120 lines incl. tests (runner.py the bulk; small additions to day_log.py and
worker_pool.py; scripts untouched). This **exceeds** the original prompt's "<30
lines / no code outside scripts / don't touch runner.py" rules — those rules were
predicated on the incorrect wiring and should be dropped for the revised PR B.

## 8. Operator CLI (unchanged by this PR)
- New default (pool):  `python scripts/run_daily.py`  /  `python scripts/run_backfill.py <handle>`
- Force sequential (if the optional fallback knob is added): e.g.
  `SEQUENTIAL=1 python scripts/run_daily.py` or `ingest_handle(handle, sequential=True)`
  in a debug shell. (Decide whether to expose a CLI/env fallback or keep the
  fallback test-only.)
