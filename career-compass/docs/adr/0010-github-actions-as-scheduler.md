# ADR-0010 — GitHub Actions is the scheduler

**Status:** Accepted · 2026-08-21

## Context

Ingestion needs to run daily without me remembering to run it. A career tool
that only updates when I feel anxious enough to open a terminal has inverted
its own value proposition — the point is that it notices things before I think
to look.

Constraints: single user, tiny workload, no infrastructure budget, no
availability requirement, and the canonical store is a SQLite file already
living in this repo (ADR-0003).

## Decision

GitHub Actions on a cron schedule, committing the updated `data/career.db`
back to the default branch — the same pattern already working in my other
repo.

- Daily ingest + normalize + extract + analyze.
- Weekly brief generation, written to `briefs/YYYY-WW.md` and committed.
- `concurrency: { group: career-refresh, cancel-in-progress: false }` so runs
  never overlap and corrupt the single-writer store.
- `ANTHROPIC_API_KEY` from repository secrets. No secrets in the repo, ever
  — the environment is the only source.
- Manual `workflow_dispatch` for on-demand runs.

The scheduler is deliberately dumb: it just asks "what is due?" Staleness
lives in `source.refresh_interval_hours` (see
`docs/03-ingestion-contracts.md`), so **adding a source never touches the
workflow file.** The cron expression is a heartbeat, not a schedule.

Failure handling: per-source isolation means a broken endpoint marks itself
failed in the run ledger and the job still commits. A job that fails entirely
sends a notification and leaves the DB untouched — a stale database is
strictly better than a half-written one.

## Alternatives considered

- **Local cron.** Free and simple, but only runs when my laptop is awake, and
  the database then lives outside git, losing the history property that
  ADR-0003 depends on.
- **A small cloud VM / serverless + hosted DB.** Correct for a real product.
  Here it adds cost, credentials, deployment, and a backup story to a workload
  measured in minutes per day.
- **Run manually.** Fails the "notices before I look" requirement, which is
  most of the point.
- **A workflow per source.** Superficially tidier, but puts scheduling
  knowledge in YAML where the database already has it, and adding a company
  would then mean editing CI config.

## Consequences

- Scheduled workflows on a private repo consume Actions minutes. The workload
  is small; if it ever matters, the interval widens.
- GitHub disables scheduled workflows on repos with no activity for 60 days.
  The daily commit is itself activity, so this is self-sustaining — but worth
  knowing.
- Cron timing is best-effort and can be delayed under load. Irrelevant at
  daily granularity.
- Automated commits to the default branch require the workflow to have write
  permission and to be the only writer. The concurrency group enforces the
  latter.
- The API key lives in GitHub secrets, giving one more reason the repo stays
  private and its Actions logs stay unshared.
