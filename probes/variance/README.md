# Variance Probe

## What it tests

Runs the same tweet-fetch query N times in a row against each provider (GetXAPI,
twitterapi.io) and compares the results. For each provider it answers:

- **Count consistency** — do repeated runs return the same number of tweets?
- **ID-set consistency** — are the returned tweet IDs the same across runs, or does
  the index return different tweets on different calls?
- **Floor completeness** — did every run reach the intended start-date boundary
  (`reached_floor=True`)?
- **Rate-limit behaviour** — how many 429s occurred, did backoff recover each one,
  or did a run abort mid-pagination?

Across providers it also measures:

- **Union lift** — how many additional tweets does combining both providers yield
  over using either alone?

---

## How to run

Trigger the **FinTwit API Variance Probe** GitHub Actions workflow
(`fintwit-variance.yml`) via `workflow_dispatch`:

| Input | Description | Default |
|-------|-------------|---------|
| `handle` | Twitter handle (without `@`) | required |
| `since` | Start date `YYYY-MM-DD` | Jan 1 of current year |
| `runs` | Number of repeat runs per provider | `3` |

The workflow saves outputs to `probes/variance/<YYYY-MM-DD>_<handle>/` and commits
them back to `main`.

---

## How to read the output

Each run folder contains:

### `report.md`

Human-readable summary. Key things to check:

- **VERDICT: STABLE** — counts within 5 % of each other, ≥ 95 % ID overlap across
  all runs of a provider, all runs reached the floor, no aborting 429s.
- **VERDICT: VARIABLE** — any of those conditions failed. Read the per-run rows
  for which runs diverged and why (floor not reached, 429-abort, ID-set spread).
- **Cross-provider union** — if the union lifts either provider's count by > 10 %,
  consider a dual-provider backfill strategy.
- **Sample tweets** — 10 representative tweets so you can eyeball whether the
  corpus is real ticker discussion vs noise.

### `<provider>_run<N>.json`

Full normalized tweet objects for every run of every provider, directly
`json.load()`-able. Fields match the `Tweet` dataclass:
`id`, `text`, `created_at_utc`, `type`, `is_reply`, `is_quote`,
all engagement counts, `has_media`, `media_urls`, `url`.

These are **offline dev fixtures**: use them to develop and test ticker extraction,
thesis generation, or sentiment analysis without making live API calls.

### `meta.md`

Auto-generated run parameters (handle, date/time, `--since`, provider names, git
SHA of main) plus the STABLE/VARIABLE verdict. Leave the `Conclusion:` line blank
for manual annotation after review.

---

## Interpreting 429 data

- **429-count = 0** — no throttling; result is a clean measure of index behaviour.
- **429-count > 0, all recovered** — transient throttling, backoff succeeded; result
  is still valid but took longer.
- **429-abort** — rate-limit retries exhausted mid-run; `reached_floor=False`;
  the result is a partial corpus. Treat this run as inconclusive and re-run later.

---

## Per-run folder naming

`probes/variance/<YYYY-MM-DD>_<handle>/`

Same-day same-handle re-runs get `_2`, `_3`, … suffixes so prior results are
never overwritten.
