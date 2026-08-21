# ADR-0003 — SQLite as the canonical store

**Status:** Accepted · 2026-08-21

## Context

One user. A few dozen companies. Low thousands of documents per year. Batch
writes from scheduled jobs; interactive reads from a CLI and eventually a
small dashboard. No concurrent writers. No availability requirement — if the
tool is down for a day, nothing happens.

There is a real temptation here to build the "grown-up" version: Postgres,
a migration framework, dbt models, an orchestrator. That temptation is worth
naming, because this repo is partly a system-design exercise and it would be
easy to mistake *practicing big-system patterns* for *good design*.

## Decision

SQLite, one file at `data/career.db`, committed to the (private) repo.

Rationale:
- Zero operational surface. No server, no container, no credentials, no
  backup story beyond `git`.
- Version-controlled data means the entire history of what I knew and when is
  in `git log`. For a system whose whole purpose is tracking change over time,
  that is a genuine feature, not a hack.
- It matches the pattern already proven in my other repo, where a
  version-controlled SQLite file updated by a scheduled Action has worked
  well.
- Real SQL. Window functions, CTEs, and joins are exactly the tools the
  analysis layer needs, and none of the aggregation is exotic.

The migration path is deliberately left open: all access goes through
`src/career_compass/store/`, and the schema is plain SQL, so moving to
Postgres later is a repository-layer change, not a rewrite.

## Alternatives considered

- **Postgres (local or hosted).** Correct at 1000× the data. Here it adds a
  daemon, credentials, and a backup story to a problem that has none of those
  needs, and it breaks the "data history is in git" property.
- **Flat files (JSON/Parquet) + pandas.** Tempting for a small dataset, but
  the relationships are genuinely relational — company → source → document →
  extraction → mention → skill. Reimplementing joins in pandas is worse SQL.
- **DuckDB.** Excellent for the analytical queries, but the workload has an
  OLTP half (upserts during ingest, run-ledger state) and SQLite handles both
  adequately. DuckDB can read the SQLite file later if analysis outgrows it.

## Consequences

- Committing a binary file means noisy diffs and a slowly growing repo. At
  this scale, acceptable. If it becomes painful, the fix is to stop committing
  the DB and rebuild from raw + config — which the ADR-0002 invariant
  guarantees is possible.
- Single writer only. The scheduled job must not overlap with itself; the run
  ledger's `running` status plus Actions' concurrency group handles this.
- No concurrent dashboard writes. The dashboard is read-only, which it should
  be anyway.
- `data/career.db` contains personal career data. Private repo, permanently.
