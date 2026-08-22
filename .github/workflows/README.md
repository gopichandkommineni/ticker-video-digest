# `.github/workflows/` — the robots

Ten automated jobs that GitHub runs for this project. They're why the dashboard
has fresh data without anyone pressing anything.

Watch them in the **Actions** tab on GitHub. Anything with "manual" below is
started there: pick the workflow → **Run workflow**.

---

## Scheduled — these run on their own

| Workflow | When | Does |
|---|---|---|
| `daily_refresh.yml` | 2am, 9am, 1pm, 5pm ET (weekdays; 2am at weekends) | **The important one.** Downloads prices, social mentions, metadata, ETF flows and congress trades; recomputes every signal; commits `data/snapshots.db` back to `main`. |
| `fintwit-daily.yml` | 2am ET daily | Fetches yesterday's tweets for every tracked handle into `data/fintwit.db`. |

The four daily-refresh times track the US trading day: overnight (market
closed), pre-market (before the 9:30am open), mid-session, and after the 4pm
close.

## Manual — you start these

| Workflow | Does |
|---|---|
| `fintwit-backfill.yml` | Fill in tweet history for one or more handles. 💸 Costs money. |
| `fintwit-schedule.yml` | Pause or resume the nightly tweet ingest. |
| `fintwit-variance.yml` | Ask both tweet providers the same question N times and compare — do they agree with themselves? |
| `subreddit_discovery.yml` | Which subreddits discuss a given stock? |
| `subreddit_catalog.yml` | Sweep the archive for finance subreddits above a subscriber floor. |
| `subreddit_metrics.yml` | Size and activity stats for named subreddits. |
| `reddit_smoke_test.yml` | "Is Reddit data still reachable?" Read-only. Run this first when Reddit numbers look wrong. |
| `cleanup_corrupt_news.yml` | Delete news rows corrupted by an old parser bug. |

Not every job has a workflow: `subreddit_match_run.py` in
`src/casino_dashboard/jobs/` is run by hand, not on a schedule.

---

## Two things that matter about how these are wired

### The `db-writer` lock

`data/snapshots.db` and `data/fintwit.db` are committed to git, so two
workflows writing at once would produce conflicting commits. Every
database-writing workflow declares:

```yaml
concurrency:
  group: db-writer
  cancel-in-progress: false
```

They queue instead of racing. `cancel-in-progress: false` matters — a queued
run **waits its turn** rather than being thrown away.

### Committing data back to `main`

`daily_refresh.yml` ends by committing the updated database:

```yaml
git add data/snapshots.db        # only this file — never `git add -A`
git commit -m "Refresh: …"
git pull --rebase origin main    # absorb anything that landed while we ran
git push origin HEAD:main
```

This is why the deployed dashboard is fast — and why you must never commit a
locally-modified database from your laptop.

---

## Secrets

Workflows read API keys from GitHub's encrypted secret store, never from the
code. To add or rotate one: repository **Settings** → **Secrets and variables**
→ **Actions**.

Currently used: `ANTHROPIC_API_KEY`, `YOUTUBE_API_KEY`, `FINNHUB_API_KEY`,
`FMP_API_KEY`, `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USERNAME`,
`REDDIT_PASSWORD`, `APIFY_TOKEN`, `GETXAPI_KEY`, `TWITTERAPI_IO_KEY`.

Non-secret settings (like `REDDIT_BACKEND`) are *variables*, on the same page
under a different tab.

---

## Reading a run

1. **Actions** tab → pick the workflow → pick a run.
2. The **Summary** tab shows the stage-by-stage report: a ✓ or ✗ per stage.
3. Click a step to see its full log.

**A green run can still contain failed stages.** Every stage of the daily
refresh is individually error-handled so one dead source can't kill the whole
run. Always read the summary, not just the badge colour.

## Common problems

| Symptom | Cause |
|---|---|
| Dashboard data is stale, no runs listed | GitHub disables scheduled workflows after 60 days without repository activity. Push a commit, or run one manually. |
| A run fails on "Install project" | A dependency changed or broke. Check `pyproject.toml`. |
| A stage fails with 401/403 | An API key expired. Rotate the secret. |
| A run fails on the commit step | Someone pushed mid-run. Usually self-healing on the next run thanks to `git pull --rebase`. |
| Reddit stages failing | Start at [docs/runbooks/reddit-local-runbook.md](../../docs/runbooks/reddit-local-runbook.md). |

## Changing the schedule

Cron times are in **UTC**, with the US Eastern equivalent in a comment. Decode
any expression at [crontab.guru](https://crontab.guru) before committing it.
Remember Eastern shifts an hour with daylight saving; UTC doesn't, so the local
time drifts twice a year — that's accepted here.
