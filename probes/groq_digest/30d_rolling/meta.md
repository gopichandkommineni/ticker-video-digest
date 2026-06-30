# Probe meta — Groq 30-day rolling (resumable ledger)

| parameter | value |
|-----------|-------|
| probe | groq_digest (30-day, accumulating) |
| script | `groq_month_probe.py` |
| folder | stable (not dated) — the ledger accumulates across runs |
| window | last 30 days (rolling at run time) |
| database | `data/fintwit.db` · `raw_tweets` (read-only) |
| provider | Groq (OpenAI-compatible API) |
| thesis model | `llama-3.1-8b-instant` |
| sector model | `llama-3.3-70b-versatile` |
| run date (UTC) | 2026-06-30 |

## Coverage

| metric | value |
|--------|-------|
| total tweets (30d) | ~2968 |
| ticker-bearing | ~741 (25.0%) |
| unique tickers | 355 |
| thesis rows in ledger | **741 / 741 (100%)** |
| sector map | complete (cached) |

## Run notes

- Full month covered in one ~12-min main run + a short resume (to fill 15
  tweets the model didn't echo and to retry the sector call). Total Groq calls
  ≈ 56; many were token-429s absorbed by `retry-after` sleeps — **$0**.
- TPM (6,000) was the binding throttle, not requests; RPD/TPD were nowhere near.
- Stage 3 sector map is **probe-only** and visibly miscategorizes some tickers
  (e.g. `$RKLB`, `$RDDT` placed under biotech). Production must use a
  deterministic ticker→sector map.
- Cloudflare blocks the default Python-urllib User-Agent (error 1010); the probe
  sets a normal UA.

Conclusion: 
