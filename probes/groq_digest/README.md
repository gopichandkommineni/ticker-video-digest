# Groq Digest Probe

Groq twin of [`gemini_digest`](../gemini_digest/README.md): the same read-only,
**descriptive-only** 30-day analysis (no buy signals, no recommendations), run
against Groq's OpenAI-compatible API instead of Gemini.

Script: `groq_month_probe.py` (repo root). Output: `30d_rolling/`.

## Why Groq (vs the Gemini probe)

The Gemini free tier caps at **20 requests/day per project** — far too low to
cover a month of tweets in one run. Groq's free tier is dramatically roomier, so
the same workload completes in a single run:

| | Gemini free | Groq free (`llama-3.1-8b-instant`) |
|---|---|---|
| Requests/day | 20 / project | **14,400** |
| Tokens/day | (low) | **500,000** |
| Binding limit here | RPD (20) | **TPM (6,000)** |
| 30-day backfill (741 tweets) | many days | **~12 min, one run** |

## Models

- **Thesis (bulk):** `llama-3.1-8b-instant` — highest free RPD/TPD; TPM (6,000)
  is the throttle, so batches are sized under it and the run paces on
  `retry-after`.
- **Sector (one call):** `llama-3.3-70b-versatile` — better quality for the
  single mapping call; retried on 429.

## Rate-limit handling

- A 429 may come from RPM / RPD / TPM / TPD. Groq returns `x-ratelimit-*`
  headers and `retry-after`; the probe honors `retry-after` (capped) and retries
  per batch, so a throttled run keeps going.
- **Cloudflare note:** the default `Python-urllib` User-Agent is 403'd by
  Cloudflare (error 1010); the probe sends a normal `User-Agent`.

## Artifacts (`30d_rolling/`)

- `thesis.jsonl` — resumable ledger, one record per `tweet_id`. Re-runs skip
  done tweets and only fill gaps; the report table is the full union.
- `sectors.json` — cached Stage 3 map (probe-only; the model **can
  miscategorize** — replace with a deterministic ticker→sector map in
  production).
- `report.md` — regenerated each run.

## How to run

```
GROQ_API_KEY=... python groq_month_probe.py
```

Stages 1–2 are deterministic (offline). Stages 3–4 need the key and network
access to `api.groq.com`.
