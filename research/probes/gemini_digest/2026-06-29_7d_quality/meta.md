# Probe meta

| parameter | value |
|-----------|-------|
| probe | gemini_digest (7-day quality) |
| script | `gemini_probe.py` |
| run date (UTC) | 2026-06-29 |
| window | last 7 days |
| database | `data/fintwit.db` · `raw_tweets` (read-only) |
| model | `gemini-2.5-flash` |
| extraction | per-tweet `{thesis, sentiment, stance}` |
| git SHA | 542bff0 |

## Coverage

| metric | value |
|--------|-------|
| pulled (7d) | 291 |
| ticker-bearing | 70 (24.1%) |
| Gemini calls (cap 50) | 50 |
| succeeded | 22 |
| rate-limited (429) | 28 |

## Notes

- Validated the strict-JSON contract: every successful call returned exactly
  `{thesis, sentiment, stance}`; cashtags extracted by regex, never the LLM.
- Confirmed correct `"none"` handling for ticker-only / emoji-only tweets and
  multilingual summarization.
- Quality flag: sentiment skews almost entirely `bullish` on this corpus — low
  discriminative power; needs sharper bearish/neutral criteria if used.
- The 28 failures are the free-tier daily quota, not code errors.

Conclusion: 
