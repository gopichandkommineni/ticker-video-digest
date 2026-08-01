# Probe meta

| parameter | value |
|-----------|-------|
| probe | gemini_digest (30-day analysis) |
| script | `gemini_month_probe.py` |
| run date (UTC) | 2026-06-29 |
| window | last 30 days |
| database | `data/fintwit.db` · `raw_tweets` (read-only) |
| model | `gemini-2.5-flash` |
| stage 4 mode | batched, 50 tweets/call |
| git SHA | 542bff0 |

## Coverage

| metric | value |
|--------|-------|
| total tweets (30d) | 3013 |
| ticker-bearing | 754 (25.0%) |
| unique tickers | 357 |
| handles with cashtags | 9 |
| thesis rows extracted | 454 of 754 |

## Notes

- Stage 3 sector map is **probe-only** (single Gemini call; can miscategorize).
- ~300 thesis rows were not extracted this run due to transient Gemini
  `503`/read-timeout on ~5 batches plus the free-tier daily call budget; a clean
  re-run on a fresh daily quota would complete all 754.
- Free-tier cap is 20 req/day **per project per model**; the two keys used drew
  from the same exhausted pool.

Conclusion: 
