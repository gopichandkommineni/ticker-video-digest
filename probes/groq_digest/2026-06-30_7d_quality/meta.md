# Probe meta

| parameter | value |
|-----------|-------|
| probe | groq_digest (7-day quality) |
| script | `groq_probe.py` |
| run date (UTC) | 2026-06-30 |
| window | last 7 days |
| database | `data/fintwit.db` · `raw_tweets` (read-only) |
| model | `llama-3.3-70b-versatile` |
| extraction | per-tweet `{thesis, sentiment, stance}` |
| git SHA | 8052001 |

## Coverage

| metric | value |
|--------|-------|
| pulled (7d) | 321 |
| ticker-bearing | 64 (19.9%) |
| Groq calls (cap 50) | 50 |
| succeeded | 50 |
| rate-limited (429) | 0 |

## Notes

- Validated the strict-JSON contract: every one of the 50 calls returned exactly
  `{thesis, sentiment, stance}` and parsed cleanly; cashtags extracted by regex,
  never the LLM. Correct `"none"` thesis handling on ticker-only / recap tweets
  (9 of 50).
- Unlike the Gemini 7-day run (sentiment skewed almost entirely bullish),
  Llama 3.3 70B showed some discrimination: **38 bullish / 6 bearish / 6
  neutral**. Stance: opinion (40), news (7), other (1), prediction (1),
  question (1).
- Zero 429s at this volume — the 7-day per-tweet pass (50 short calls, 2.1s
  apart) stays under the per-minute token bucket. Rate limiting only bites on the
  batched 30-day pass.
- Cloudflare blocks the default `Python-urllib` User-Agent with a 403 (error
  `1010`); the probe sets an explicit `User-Agent` header to clear it.

Conclusion: 
