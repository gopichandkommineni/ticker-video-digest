# Probe meta

| parameter | value |
|-----------|-------|
| probe | groq_digest (30-day analysis) |
| script | `groq_month_probe.py` |
| run date (UTC) | 2026-06-30 |
| window | last 30 days |
| database | `data/fintwit.db` · `raw_tweets` (read-only) |
| model | `llama-3.3-70b-versatile` |
| stage 4 mode | batched, 25 tweets/call |
| git SHA | 8052001 |

## Coverage

| metric | value |
|--------|-------|
| total tweets (30d) | 3032 |
| ticker-bearing | 747 (24.6%) |
| unique tickers | 358 |
| handles with cashtags | 9 |
| thesis rows extracted | 475 of 747 |

## Notes

- Stage 3 sector map is **probe-only** (single Groq call; can miscategorize),
  cached to `sectors.json` and reused across re-runs with no extra quota.
- The binding constraint on Groq's free tier is **tokens-per-minute, not
  requests-per-day** — the mirror image of Gemini. Headers report ~1,000 req/day
  but only ~12,000 tokens/min for `llama-3.3-70b-versatile`. The batched thesis
  pass exhausts the per-minute token bucket within a few batches, and across the
  session the **daily token allowance** was consumed — the remaining ~272 tweets
  429'd persistently and were deferred. The resumable ledger (`thesis.jsonl`)
  lets a later run on a fresh daily budget complete all 747.
- Stance distribution over the 475 extracted: opinion (248), news (113),
  other (56), prediction (44), question (8), promotion (6).
- Cloudflare blocks the default `Python-urllib` User-Agent with a 403 (error
  `1010`); the probe sets an explicit `User-Agent` header to clear it.
- `groq_month_probe.py` honours the `retry-after` / `x-ratelimit-reset-tokens`
  header and waits out the per-minute bucket; `GROQ_MAX_429_RETRIES` tunes how
  many times (set to `0` to regenerate the report fast once the daily budget is
  spent).

Conclusion: 
