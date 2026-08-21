# 01 — Architecture

## Shape

A batch pipeline with an immutable landing zone and a replayable tail. Seven
stages, each with a single responsibility and an explicit contract to the
next:

```
                 ┌──────────────────────────────────────────────┐
                 │  config/companies.yaml + config/sources.yaml  │
                 └───────────────────────┬──────────────────────┘
                                         │ declares what exists
                                         ▼
  ┌─────────┐   ┌──────────┐   ┌──────────────┐   ┌───────────────┐
  │ SOURCES │──▶│ INGEST   │──▶│  RAW STORE   │──▶│  NORMALIZE    │
  │ adapters│   │ fetch +  │   │ content-     │   │ parse → common│
  │         │   │ ledger   │   │ addressed,   │   │ Document      │
  │ rss     │   │          │   │ immutable    │   │               │
  │ ats.*   │   │          │   │ (files+hash) │   │               │
  │ manual  │   │          │   │              │   │               │
  └─────────┘   └──────────┘   └──────────────┘   └───────┬───────┘
                                                          │
                                                          ▼
  ┌──────────┐   ┌──────────────┐   ┌────────────┐   ┌──────────────┐
  │ SURFACES │◀──│   ANALYSIS   │◀──│  EXTRACT   │◀──│  CANONICAL   │
  │ cli      │   │ demand,      │   │ LLM → typed│   │  STORE       │
  │ brief    │   │ supply, gap, │   │ insights,  │   │  SQLite      │
  │ dashboard│   │ prep plan    │   │ versioned  │   │              │
  └──────────┘   └──────┬───────┘   └────────────┘   └──────────────┘
                        │                                   ▲
                        │                                   │
                        └───── profile/resume.yaml ─────────┘
                               (supply side)
```

## The stages

### 1. Sources
Declarative. `config/companies.yaml` lists who I care about;
`config/sources.yaml` binds each company to concrete feeds and endpoints. An
*adapter* is code; a *source* is a config row that names an adapter and its
parameters. Adding Spotify is a YAML edit if it uses an ATS we already speak
(ADR-0004).

### 2. Ingest
Fetch, respecting rate limits and `robots.txt`. Writes bytes and provenance;
interprets nothing. Every run opens a row in the **run ledger**, so a partial
failure is visible and resumable rather than silently halving a dataset.

### 3. Raw store
Content-addressed: `data/raw/<sha256[:2]>/<sha256>.<ext>`, with a row in
`raw_document` carrying URL, fetch time, HTTP status, and content type.

Two properties fall out of hashing for free:
- **Dedupe.** A job posting re-listed under a new URL hashes identically and
  is not counted twice.
- **Change detection.** A JD whose text changed produces a new hash, and the
  diff between versions is itself signal ("they added *distributed systems
  design* to the requirements in March").

Raw is **append-only**. Nothing downstream may edit it.

### 4. Normalize
Adapter-specific parsing (`text/html` → text, Greenhouse JSON → fields, an
RSS entry → a post) into one common `Document`, plus a `job_posting` row when
the document is a posting. Deterministic, no network, no LLM — so it is cheap
to re-run over the entire raw store after a parser fix.

### 5. Extract
The only LLM stage. Two passes, mirroring a pattern that already works:
- **Per-document:** one `Document` in, one typed `DocumentInsights` out
  (themes, named systems, explicit requirements, seniority signals, skill
  mentions against the taxonomy, each with a verbatim quote).
- **Cross-document:** many `DocumentInsights` for one company in, one
  `CompanyProfile` out (recurring themes ranked by independent-source count,
  their design vocabulary, the problems they keep describing).

Every output row records `extractor_version`, `model`, and `schema_version`
so a prompt change is a re-derivation, not a migration (ADR-0007). Prompt
caching goes on the system prompt + taxonomy block, which are constant across
every call in the per-document pass.

**Extraction never invents skills.** It may only emit slugs that exist in
`taxonomy/skills.yaml`, plus an `unmapped[]` list of phrases it could not
place. That list is the input to taxonomy maintenance — the system tells me
when my vocabulary is stale instead of silently drifting (ADR-0005).

### 6. Analysis
Pure functions over the canonical store, no network, no LLM, fully
deterministic and unit-testable:
- `demand(company, skill, window)` — from extractions, recency-decayed.
- `supply(skill)` — from `profile/resume.yaml` + the evidence ledger.
- `gap = f(demand, supply)` — and a *leverage* ranking on top.
- `prep_plan(company)` — top gaps turned into concrete actions.

See `docs/05-gap-scoring.md`. Deterministic scoring is deliberate: I want to
be able to argue with the number, and to see exactly which document moved it.

### 7. Surfaces
- `career brief <company>` — the "what do I say in the room" one-pager.
- `career gaps [--company X]` — ranked gaps with evidence links.
- `career diff --since 7d` — what changed.
- `career plan` — this month's prep items.
- A small Streamlit dashboard over the same queries, later.

## Cross-cutting

**Run ledger.** Every job writes `run(job_name, started_at, finished_at,
status, stats_json)`. Jobs are idempotent and resumable: re-running an
interrupted ingest re-fetches only what is missing or stale.

**Staleness, not schedules, drives work.** A source carries
`refresh_interval`; the scheduler asks "what is due?" rather than each job
knowing its own cron. Adding a source doesn't touch the workflow file.

**Configuration is data, code is generic.** No file under
`src/career_compass/` should contain the string `"netflix"`.

**Failure is per-source.** One 500 from one endpoint marks that source failed
in the ledger and the run continues. A career tool that goes dark because one
careers page changed its markup is worse than useless.

## Why not something else

| Alternative | Why not |
|---|---|
| Postgres + dbt + Airflow | The dataset is thousands of rows. The operational cost dwarfs the problem (ADR-0003). |
| Vector store + RAG over raw docs | Retrieval-only gives plausible prose, not a stable, diffable score. The taxonomy exists precisely so this is countable (ADR-0005). Embeddings are still useful *inside* taxonomy mapping. |
| One adapter per company | 40 companies, ~6 ATS platforms. Adapter-per-company is 34 redundant implementations (ADR-0004). |
| A SaaS job-alert tool | It optimizes for application volume. This optimizes for credibility, and the profile side is the whole point. |
| Skip raw, parse on fetch | A parser bug or a better model then costs a full re-crawl, and some sources cannot be re-fetched at all (ADR-0002). |
