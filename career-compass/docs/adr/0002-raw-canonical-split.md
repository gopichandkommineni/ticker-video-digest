# ADR-0002 — Immutable raw store, replayable derivation

**Status:** Accepted · 2026-08-21

## Context

The pipeline turns fetched bytes into scores through several lossy steps:
parse → LLM extract → aggregate. Each will be wrong at some point:

- Parsers break when a feed or an API changes shape.
- LLM extraction improves with better prompts and better models — the output
  in six months will be materially better than today's for the same input.
- The skill taxonomy will grow, and old documents should be re-read against
  the new vocabulary.

Meanwhile, much of the source data is **not re-fetchable**. Job postings close
and disappear. Blogs get restructured. A manually pasted JD from behind a
login exists exactly once, in my clipboard, on one afternoon.

If the pipeline parses on fetch and stores only the result, every improvement
downstream requires re-crawling — and for the most valuable documents, that is
simply impossible.

## Decision

Split storage into **raw** (immutable, content-addressed, append-only) and
**derived** (freely rebuildable).

- Ingest writes bytes to `data/raw/<sha256[:2]>/<sha256>` plus a
  `raw_document` provenance row. It interprets nothing.
- `normalize` is a **pure function** of raw bytes: no network, no clock, no
  randomness. Same bytes in, same `Document` out.
- Extraction and analysis read from canonical and write only to derived
  tables.

The invariant, which is testable: `DELETE FROM extraction; DELETE FROM
company_skill_demand; DELETE FROM gap;` followed by a re-run must reproduce
identical state, with zero network calls.

Content-addressing rather than URL-keying gives two things for free: dedupe
across URLs (a re-listed posting hashes the same) and change detection (a new
hash for the same `external_id` means the text changed, and the diff is
itself signal).

## Alternatives considered

- **Parse on fetch, store only parsed.** Simplest, and the only one that is
  outright wrong for this domain: it makes the most valuable documents
  unimprovable.
- **Store raw as a BLOB in SQLite.** Works, but bloats the version-controlled
  DB file and makes `grep` over the corpus awkward. Files on disk are easier
  to inspect, and inspection is how parser bugs get found.
- **Keep raw, but key by URL.** Loses dedupe and makes change detection a
  string comparison against the previous fetch. Hashing is strictly better for
  the same effort.

## Consequences

- Disk grows monotonically. At a few thousand documents a year, irrelevant.
- Two-step ingestion (fetch, then normalize) instead of one. Accepted: it is
  also what makes per-source failure isolation clean, since a `parse_error`
  still leaves the bytes safely stored.
- Re-derivation must be cheap enough to actually run, which constrains
  `normalize` to stay pure. That constraint is a feature.
- Raw payloads may contain content whose terms restrict redistribution — one
  more reason this repo stays private (`docs/08-legal-and-etiquette.md`).
