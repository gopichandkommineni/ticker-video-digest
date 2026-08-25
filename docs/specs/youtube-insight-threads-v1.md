# YouTube Insight Threads — Design Specification v1.0

**Project:** Casino-Coherent Momentum Dashboard
**Date locked:** 2026-08-24
**Status:** Shipped. Implemented in `src/ticker_digest/`.
**Amended by:** `youtube-insight-threads-v2.md` — the *Novelty detection*
and *Storage* sections below describe the original single-citation claim
ledger, which v2 replaced with a claims/citations split.
**Code:** `pipeline.py`, `sources.py`, `quality.py`, `novelty.py`, `thread.py`, `store.py`

---

## Purpose

Answer one question: *"Did anything new get said about this company on YouTube
this week?"*

A lot of people record videos about a stock. Most of them are restating the
same bull case. The value is not "summarise these videos" — it is the delta
between what was said this week and what was already on record.

This is **not** a video recommender, and **not** a sentiment tracker. It reads
transcripts, extracts claims, works out which claims are new, and writes a
thread about them.

---

## Design principles

- **The delta is the product.** A run where nothing is new must say so plainly
  rather than manufacture significance.
- **Deterministic before probabilistic.** Filtering, ranking and duplicate
  detection are pure functions with unit tests. The LLM does judgement calls
  the code can't: extraction, paraphrase matching, writing.
- **Every claim is clickable.** No claim reaches the user without a video id
  and a timestamp. Citations to videos the run never read are dropped.
- **One bad video is not a failed run.** Missing captions, an extraction error,
  a channel that never mentioned the ticker — reported and skipped.
- **Cost scales with videos, not with ambition.** The per-video pass uses the
  cheaper model; the strong model is called once, at the end.

---

## Two ways in

The user either knows *where* to look or only knows *what* they care about.

| Input | Meaning | Path |
|---|---|---|
| **Ticker** — `ticker RKLB` | "Find me reliable sources" | YouTube search → quality filter → reliability ranking → top N |
| **Channel** — `ticker RKLB --channel @spaceinvesting` | "I already trust this person" | Resolve channel → their uploads, narrowed to the ticker → same filter and ranking |

The channel input accepts a name, an `@handle`, a channel URL or a raw channel
id. A name that resolves to nothing is an error, not a silent fallback to
search — digesting the wrong creator is worse than digesting nobody.

A ticker is required in both cases. It is the key everything is stored under,
and the thing novelty is judged against.

### Quality filter (before spending a transcript call)

Drop the video if it is under 120 seconds, if the channel has under 500
subscribers, or if the title is shouted or carries more than one hype emoji.
The ticker symbol is excluded from the ALL-CAPS test — every ticker is
upper-case by definition.

### Reliability ranking

Each surviving video scores 0–1 on five log-scaled components:

| Component | Weight | Reads as |
|---|---|---|
| Subscribers | 30% | Does anyone listen to this channel |
| Views | 25% | Did anyone watch this video |
| Views per subscriber | 15% | Did this one travel beyond the regulars |
| Duration | 15% | Analysis or a hot take |
| Recency | 15% | Commentary against current facts |

Views-per-subscriber is deliberate: a 2k-subscriber channel with a 30k-view
video said something people passed around, and outranking a quiet 400k-sub
channel is the intended behaviour, not a bug. Weights live in
`core/config.py`.

---

## Pipeline

```
select videos → transcripts (30-day cache) → per-video extraction (Sonnet)
             → claims → novelty check → thread (Opus) → SQLite
```

**Per-video extraction** is the existing two-pass design's first pass: a
transcript in, a `VideoInsights` out — catalysts, red flags, upcoming events
and sentiment, each carrying `timestamp_seconds`. Prompt caching is on the
system prompt and schema, which are identical for every video.

**Claims** flattens those extractions into one list, collapsing duplicates
inside the batch: three videos reporting one contract win produce one claim.

---

## Novelty detection

Two stages, cheap first.

**Stage 1 — deterministic.** Normalise each claim to a stopword-free token set
and fingerprint it. An exact fingerprint match against a stored claim, or a
Jaccard similarity at or above 0.72, is a restatement — marked `known` with no
model call.

**Stage 2 — LLM.** Survivors go to the model *with* the stored claims as
context, and come back as one of:

| Verdict | Definition |
|---|---|
| `new` | Nothing on record covers this |
| `developing` | Something on record covers the subject; this adds a date, a figure, a confirmation |
| `known` | A paraphrase stage 1 missed |

Skipped entirely when there is no history (first run for a ticker) or nothing
survived stage 1. A claim the model fails to classify stays `new` —
under-reporting news is the worse failure, and the citation is there to check.

The comparison window is 90 days.

---

## The thread

The stored deliverable. At most 8 posts, ordered `new` → `developing`, with
`known` claims included only as context or where several sources newly agreed.
Each post is one idea, in plain language, attributed to the commentators rather
than asserted as fact, and carries the citations for the claims it covers.

Post-processing the model does not get to skip:

- positions are numbered here, not by the model
- `new_claim_count` is counted here
- citations naming a video this run never read are dropped
- the disclaimer is attached unconditionally

---

## Storage

`data/digests.db` — separate from the dashboard's `snapshots.db`, git-ignored,
overridable with `TICKER_DIGEST_DB`.

| Table | Holds |
|---|---|
| `digest_runs` | The whole run as JSON, keyed by run id |
| `claims` | One row per distinct claim per ticker |
| `threads` | The thread as JSON, keyed by thread id |

`claims.first_seen_at` is written with `ON CONFLICT DO NOTHING`. A claim seen
again keeps the date it was *first* seen — that column is the novelty check.

---

## What this does not do

- **No scheduled job.** Runs are on demand from the CLI. Wiring it into
  `daily_refresh.yml` across the universe would multiply YouTube quota by 64
  and Anthropic spend by however many videos each ticker attracts — a decision
  worth making explicitly, later.
- **No dashboard page.** The threads are stored and readable from the CLI. A
  Streamlit page reading `data/digests.db` is the obvious next step.
- **No cross-ticker synthesis.** A claim about a sector shows up under whatever
  ticker was requested.
- **No speaker reputation.** Reliability is measured on the channel's audience,
  not on whether their past calls were right. Tracking that needs outcome data
  this project doesn't collect yet.

---

## Disclaimer

The output is aggregated commentary from public YouTube videos. It is not
investment advice, and every generated thread carries that line.
