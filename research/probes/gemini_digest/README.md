# Gemini Digest Probe

## What it tests

A read-only quality/feasibility probe for using **Gemini** to summarize FinTwit
tweets into structured fields. It answers two empirical questions:

- **Quality** — given a ticker-bearing tweet, can `gemini-2.x-flash` return a
  reliable strict-JSON `{thesis, claim, stance}` structure (no ticker
  extraction — that stays deterministic via regex)?
- **Feasibility at scale** — does a 30-day, all-handles run fit within the
  Gemini free-tier request budget, and what does the resulting descriptive
  picture (volume, per-handle ticker concentration, sector mix) look like?

> **Descriptive only — not investment advice.** These probes measure *what
> handles are posting*. They contain no buy signals, no ranking of tickers by
> attractiveness, and no recommendations.

The probe is **read-only** on `data/fintwit.db` (`raw_tweets`): no DB writes, no
schema changes, no new tables.

---

## Architecture notes (important)

- **Cashtags are extracted deterministically** with `\$[A-Z]{1,5}\b`, never by
  the LLM. The regex filter runs *before* any Gemini call, which both matches
  the production design and protects the free-tier quota.
- **Sector mapping (Stage 3) is probe-only.** It is produced by a single Gemini
  call and the model can miscategorize. In production it would be replaced by a
  deterministic ticker→sector map.
- **Free-tier quota is the binding constraint.** `gemini-2.x-flash` free tier
  caps at **20 requests/day, per project, per model**. Multiple API keys from
  the same project share that pool. The 30-day thesis stage therefore **batches
  ~50 tweets per call** so the whole month fits in well under 20 calls; a naive
  per-tweet design cannot complete on free tier.

---

## How to run

Both probes read `GEMINI_API_KEY` from the environment (never hardcoded) and
print to the terminal while writing a markdown report.

| Script | Scope | Output |
|--------|-------|--------|
| `gemini_probe.py` | last 7 days, per-tweet `{thesis, sentiment, stance}` | terminal |
| `gemini_month_probe.py` | last 30 days, 4-stage analysis, batched thesis | `report.md` |

Rate-limiting is built in: a politeness delay keeps calls under 15/min, every
`429` is caught per-call and the run continues, and a daily-budget guard stops
before the 20-call wall. The run always completes even if many calls fail.

---

## How to read the output

Each run folder is named `probes/gemini_digest/<YYYY-MM-DD>_<scope>/` and
contains:

### `report.md`

- **Funnel** — total tweets vs. ticker-bearing (cashtag ratio).
- **Per-handle ticker profile** (deterministic) — which tickers each handle
  mentioned and how often.
- **Sector concentration** (probe-only LLM) — overall and per-handle.
- **Thesis table** — `{thesis, claim{falsifiable, horizon, checkpoint},
  stance}` per ticker-bearing tweet, plus a stance distribution.
- **Run summary** — Gemini calls attempted/succeeded/rate-limited.

### `meta.md`

Run parameters (window, model, DB, git SHA) plus coverage notes. Leave the
`Conclusion:` line blank for manual annotation after review.

---

## Interpreting 429 / coverage data

- **429-count = 0** — clean run; coverage reflects true extraction quality.
- **429s present** — the daily free-tier budget was hit (or shared across keys);
  remaining tweets are skipped, not failed. Re-run after the daily reset.
- **Transient `503` / read-timeout** — Gemini-side, not quota. The probe retries
  these within the remaining daily budget; any still-uncovered batches are noted
  in the report and can be recovered on a later run.
