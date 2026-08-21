# ADR-0006 — Manual input is an adapter, not an exception

**Status:** Accepted · 2026-08-21

## Context

A large share of the best career signal is not automatable:

- Postings behind a login or on a referral-only page.
- What someone inside the company says over coffee.
- A talk with no transcript.
- A recruiter's phrasing of the actual screening bar.
- My own considered read of a posting.

The default architectural instinct is to build the automated pipeline first
and bolt on a "manual entry" form later. That reliably produces a second-class
path: different storage, different schema, excluded from scoring, and
therefore never used. The highest-value data ends up in a notes app.

The user named this constraint up front — *"a lot of things might need manual
intervention"* — so it is a design input, not a limitation.

## Decision

Manual input is implemented as source adapters satisfying the same
`SourceAdapter` protocol as everything else. Manually entered content flows
through the identical path: raw store → normalize → extract → score.

Four entry points, all first-class:

1. **`manual.inbox`** — markdown files with YAML front-matter dropped in
   `manual/inbox/`, hashed and stored exactly like a fetched payload.
2. **Annotations** — a note attachable to any row, and pinned notes appear
   **verbatim** in briefs. The LLM never paraphrases them; summarizing my own
   intel back to me destroys its value.
3. **Overrides** — post-scoring adjustments in `config/overrides.yaml`, each
   requiring a `reason`, and *adjusting rather than deleting*: a suppressed row
   still exists and still shows under `--show-suppressed`. A tool that lets me
   silently hide inconvenient findings would converge on telling me what I
   want to hear, which is precisely the failure mode a career tool cannot
   have.
4. **Taxonomy curation** — the `unmapped[]` review loop (ADR-0005).

This also has a second-order benefit: it makes the polite path the convenient
path. When a site is behind bot protection, the answer is not a better
scraper — it is to open the page like a person and paste it
(`docs/08-legal-and-etiquette.md`).

## Alternatives considered

- **Automate first, manual entry later.** The failure mode described above.
- **A separate `notes/` directory outside the pipeline.** Easy, and produces
  data that never influences a single score.
- **A web form / TUI for entry.** Better ergonomics eventually, but a markdown
  file in a watched directory works with every editor and every phone, needs no
  code, and survives the tool being broken.

## Consequences

- Manual documents need explicit `company` and `kind` in front-matter, since
  there is no source config to infer from. Validated on ingest, fails loudly.
- Content addressing means re-dropping the same file is a harmless no-op.
- `confidence` in front-matter lets a secondhand rumor be scored lower than a
  copied posting, without excluding it.
- Overrides can hide real problems from me. Mitigated by requiring a reason
  and keeping suppressed rows visible on request.
