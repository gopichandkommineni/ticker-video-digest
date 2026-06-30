# Probe meta — 30-day rolling (resumable ledger)

| parameter | value |
|-----------|-------|
| probe | gemini_digest (30-day, accumulating) |
| script | `gemini_month_probe.py` |
| folder | **stable** (not dated) — the ledger accumulates across runs |
| window | last 30 days (rolling at run time) |
| database | `data/fintwit.db` · `raw_tweets` (read-only) |
| model | `gemini-2.5-flash` |
| stage 4 mode | batched, 50 tweets/call, resumable via `thesis.jsonl` |

## Artifacts

- `thesis.jsonl` — one record per `tweet_id` already extracted. Re-runs skip
  these and only process the remainder; the report table is rebuilt from the
  full union. This is how coverage accumulates across daily quota resets.
- `sectors.json` — cached Stage 3 sector map (355 tickers); reused so no Gemini
  call is re-spent on sectors.
- `report.md` — regenerated each run from the deterministic stages + the full
  ledger.

## Status

| metric | value |
|--------|-------|
| ticker-bearing tweets (window) | ~741 |
| thesis rows in ledger | 100 (and growing) |
| sector map | complete (cached) |

To extend coverage: run `gemini_month_probe.py` with a `GEMINI_API_KEY` that has
remaining daily free-tier budget (20 req/day **per project**, so a key from a
*different* project or a billing-enabled key adds a fresh pool). Each run appends
to the ledger until all ~741 are covered.

Conclusion: 
