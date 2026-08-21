# Career Compass

A personal career intelligence system. Tracks target companies, ingests their
public engineering signal, and maps it against an evidence-backed model of my
own experience to produce a prioritized prep plan.

Read `README.md`, then `docs/01-architecture.md`. Decisions are in `docs/adr/`.

## Status: design phase

Architecture, data model, contracts, taxonomy, and scoring model are
specified. `src/career_compass/` contains typed stubs raising
`NotImplementedError` — they define the seams, not the behavior. Nothing
fetches anything yet. Build order is `docs/07-roadmap.md`.

## Architecture

```
sources → ingest → raw store → normalize → canonical → extract → analysis → surfaces
```

- `src/career_compass/sources/` — adapters, one per ATS **platform**, not per company
- `src/career_compass/ingest/` — fetch, politeness, content-addressed raw store
- `src/career_compass/normalize/` — pure parsing into the common `Document`
- `src/career_compass/extract/` — the only LLM stage; two passes, versioned output
- `src/career_compass/analysis/` — pure scoring: demand, supply, gap, plan
- `src/career_compass/store/` — SQLite, the only place SQL is written
- `src/career_compass/surfaces/` — CLI and briefs

## Invariants — do not break these

1. **No company names in code.** `config/companies.yaml` and
   `config/sources.yaml` are the only place a company appears. If a task
   seems to require `if company == "netflix"`, the design is wrong (ADR-0004).
2. **Raw is append-only.** Nothing downstream of ingest may modify
   `data/raw/` or `raw_document`. Deleting every derived table and re-running
   must reproduce identical state with zero network calls (ADR-0002).
3. **`normalize` is pure.** No network, no clock, no randomness. Same bytes
   in, same documents out.
4. **No LLM in `analysis/`.** Scores must move only when data or config moves.
5. **No magic numbers in scoring.** Every constant lives in
   `config/scoring.yaml`.
6. **The extractor may only emit taxonomy slugs.** Unrecognized phrases go to
   `unmapped[]` for human review. Never auto-extend the taxonomy — it
   destroys month-over-month comparability (ADR-0005).
7. **Every score carries its rationale.** Document ids and verbatim quotes,
   always.
8. **Pinned annotations are never LLM-summarized.** They reach the brief word
   for word (ADR-0006).
9. **Overrides adjust, they never delete.** A suppressed row stays queryable
   with its reason (ADR-0006).
10. **Sources ship `verified: false`** and are excluded from analysis until a
    human confirms real data came back. A dead endpoint reads as "not hiring",
    which is the most dangerous wrong answer this system can give.

## Conventions

- Type hints on every function signature.
- Pydantic models at every data boundary.
- No secrets in code — `ANTHROPIC_API_KEY` from the environment only.
- No network calls in unit tests; use `tests/fixtures/`.
- Log INFO for user-visible progress, DEBUG for diagnostics.
- Politeness is enforced centrally in `FetchContext`, never per adapter. No
  override flag exists — see `docs/08-legal-and-etiquette.md` before touching
  anything in `ingest/`.

## Canonical files — do not modify without an explicit instruction

- `taxonomy/skills.yaml` — the controlled vocabulary. Renames break historical
  scores and require a `renames:` entry plus a version bump.
- `config/scoring.yaml` — the thesis, as numbers.
- `profile/resume.yaml` — hand-maintained. **Nothing in the system writes to
  it** (ADR-0008).

## Privacy

Private repo, permanently. `profile/resume.yaml`, `data/career.db`, and
`manual/` hold personal career data and candid self-assessment. Never
redistribute ingested third-party content.
