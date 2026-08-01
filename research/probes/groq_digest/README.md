# Groq Digest Probe

## What it tests

A read-only quality/feasibility probe for using **Groq** (Llama 3.3 70B,
OpenAI-compatible API) to summarize FinTwit tweets into structured fields. It is
the direct counterpart of the [`gemini_digest`](../gemini_digest/README.md)
probe — same pipeline, same strict-JSON contracts — so the two providers can be
compared head to head. It answers two empirical questions:

- **Quality** — given a ticker-bearing tweet, can `llama-3.3-70b-versatile`
  return a reliable strict-JSON `{thesis, claim, stance}` structure (no ticker
  extraction — that stays deterministic via regex)?
- **Feasibility at scale** — does a 30-day, all-handles run fit within the Groq
  free-tier budget, and what does the resulting descriptive picture (volume,
  per-handle ticker concentration, sector mix) look like?

> **Descriptive only — not investment advice.** These probes measure *what
> handles are posting*. They contain no buy signals, no ranking of tickers by
> attractiveness, and no recommendations.

The probe is **read-only** on `data/fintwit.db` (`raw_tweets`): no DB writes, no
schema changes, no new tables.

---

## Architecture notes (important)

- **Cashtags are extracted deterministically** with `\$[A-Z]{1,5}\b`, never by
  the LLM. The regex filter runs *before* any Groq call, which both matches the
  production design and protects quota.
- **Sector mapping (Stage 3) is probe-only.** It is produced by a single Groq
  call and the model can miscategorize. In production it would be replaced by a
  deterministic ticker→sector map.
- **JSON mode** uses Groq's `response_format: {"type": "json_object"}` (the
  OpenAI-compatible field), so the model is constrained to emit a JSON object.
  The Stage-4 batch prompt therefore returns `{"results": [...]}` rather than a
  bare array.
- **Cloudflare bot filter.** Groq's endpoint sits behind Cloudflare, which 403s
  (error code `1010`) the default `Python-urllib` User-Agent. The probe sets an
  explicit `User-Agent` header to clear the filter.
- **The binding constraint is tokens-per-minute, not requests-per-day** — the
  mirror image of Gemini. The free tier for `llama-3.3-70b-versatile` allows
  ~1,000 requests/day but only **~12,000 tokens/minute**. Batched thesis calls
  exhaust the per-minute token bucket long before the daily request cap, so 429s
  are *transient*: the bucket refills within ~60s. The month probe honours the
  `retry-after` / `x-ratelimit-reset-tokens` header and waits the bucket out, so
  a patient run completes the full month.

---

## How to run

Both probes read `GROQ_API_KEY` from the environment (never hardcoded) and print
to the terminal while writing a markdown report.

| Script | Scope | Output |
|--------|-------|--------|
| `groq_probe.py` | last 7 days, per-tweet `{thesis, sentiment, stance}` | terminal |
| `groq_month_probe.py` | last 30 days, 4-stage analysis, batched thesis | `report.md` |

Rate-limiting is built in: a politeness delay paces calls, every `429` is caught
and the month probe waits for the token bucket to refill before retrying, and a
resumable ledger (`thesis.jsonl`) lets a later run pick up any tweets not yet
covered. The run always completes even if many calls are throttled.

---

## How to read the output

Each run folder is named `probes/groq_digest/<YYYY-MM-DD>_<scope>/` and contains:

### `report.md`

- **Funnel** — total tweets vs. ticker-bearing (cashtag ratio).
- **Per-handle ticker profile** (deterministic) — which tickers each handle
  mentioned and how often.
- **Sector concentration** (probe-only LLM) — overall and per-handle.
- **Thesis table** — `{thesis, claim{falsifiable, horizon, checkpoint},
  stance}` per ticker-bearing tweet, plus a stance distribution.
- **Run summary** — Groq calls attempted/succeeded/rate-limited.

### `meta.md`

Run parameters (window, model, DB, git SHA) plus coverage notes. Leave the
`Conclusion:` line blank for manual annotation after review.

### `thesis.jsonl` / `sectors.json`

Resumable artifacts (not DB writes): one JSON line per extracted tweet, and the
cached probe-only sector map. Re-running only processes tweets not already in
the ledger and reuses the cached sector map, spending no extra quota.

---

## Interpreting 429 / coverage data

- **429-count = 0** — clean run; coverage reflects true extraction quality.
- **429s present** — the per-minute token bucket was hit. These are transient,
  not failures: the month probe waits out the reset and retries, and the ledger
  recovers anything still uncovered on a later run.
- **Transient `503` / read-timeout** — Groq-side, not quota. The probe retries
  these within the remaining budget; any still-uncovered batches are noted in the
  report and can be recovered on a later run.
