# ADR-0007 — LLM extractions are versioned and additive

**Status:** Accepted · 2026-08-21

## Context

The extraction stage turns a document into structured insight using a model
and a prompt. Both will change repeatedly:

- Prompts get tuned as I see what the model misreads.
- Better models ship every few months.
- The output schema grows fields.
- The taxonomy grows, so old documents should be re-read against new
  vocabulary.

If extraction results are stored as "the" answer for a document, every one of
those changes is a destructive migration. Worse, I lose the ability to check
whether a change actually helped — the old answers are gone, so "the new
prompt is better" is a feeling.

There is also a cost dimension. Extraction is the only stage that costs money
per document. Re-running it blindly on every change is both wasteful and slow.

## Decision

Extractions are **additive and versioned**. The `extraction` table has
`UNIQUE (document_id, extractor_version, schema_version)` and rows are never
updated in place.

- A prompt change bumps `extractor_version` (`doc-v3` → `doc-v4`).
- A schema change bumps `schema_version`.
- Both old and new rows coexist for the same document.
- Analysis reads **only** the version pinned in `config/scoring.yaml`, so
  producing new extractions is safe and invisible until the pin moves.

This makes prompt iteration an experiment rather than a migration: run `v4`
over a 50-document sample, diff `v3` vs `v4` on the same inputs, look at the
disagreements, then move the pin or throw `v4` away.

Each row also records `model`, `input_tokens`, `output_tokens`, and
`cost_usd`, so "what does a full re-extraction cost?" is a query rather than a
guess.

Structural details that follow:
- Output is a validated pydantic model, so a malformed response is a retry,
  not a corrupt row.
- The system prompt and the serialized taxonomy are identical across every
  call in a pass, so prompt caching applies to the large constant prefix.
- A deterministic alias pre-pass runs first and is stored alongside, giving a
  non-LLM baseline. Large divergence between the two is a signal that
  something is wrong with the prompt.

## Alternatives considered

- **Overwrite on re-extraction.** Simplest, and loses the ability to evaluate
  a change. Also makes a bad prompt an unrecoverable event.
- **Only ever store the latest, keep old prompts in git.** Git has the prompt
  but not the *outputs*, and the outputs are what you compare.
- **Re-extract everything on every change.** Cost and latency scale with
  corpus size for a change that may be reverted an hour later.

## Consequences

- The `extraction` table is the largest in the database. Fine — it is JSON
  text at a scale of thousands of rows.
- `career extract --gc --keep-versions 2` will eventually be wanted.
- Every analysis result must record which extractor version produced it, or a
  step change in a trend line becomes unexplainable.
