# ADR-0005 — A hand-curated skill taxonomy is the join key

**Status:** Accepted · 2026-08-21

## Context

The central operation is comparing *what companies want* against *what I
have*. Both sides arrive as prose. The obvious implementation is to hand both
to an LLM and ask for a gap analysis.

That produces something fluent, plausible, and useless for this purpose, for
three reasons:

1. **It is unstable.** Ask twice, get two different emphases. There is no
   sense in which last month's answer and this month's are comparable, so
   "what changed" — one of the five success criteria — cannot be answered.
2. **It is uncountable.** "Netflix seems to value distributed systems" cannot
   be ranked against "Google seems to value distributed systems," and neither
   can be trended.
3. **It is unfalsifiable.** When the output says I should learn X, I cannot
   check *why* without re-reading everything myself, which is the work the
   system was supposed to do.

## Decision

Neither side is ever compared to the other directly. Both project into a
**controlled vocabulary** — `taxonomy/skills.yaml`, a hand-curated,
versioned, three-level tree of skill slugs with alias lists — and all
comparison happens in that space with deterministic arithmetic.

The LLM's role is narrowed to one job it is genuinely good at: reading a
document and mapping phrases to slugs, with a verbatim quote for each. It may
**only** emit slugs that exist in the taxonomy. Phrases it cannot place go to
`unmapped[]`, which becomes a human review queue.

Crucially, the thesis of this whole project — that design skills matter more
than tool skills — is expressed as **branch weights in
`config/scoring.yaml`**, not as taxonomy structure. The taxonomy describes the
world; the weights describe my bet about it. If the bet is wrong, one number
changes and the entire history rescores.

## Alternatives considered

- **Free-form LLM comparison.** Unstable, uncountable, unfalsifiable. Fails
  three of five success criteria.
- **Embeddings + cosine similarity.** Stable and countable, but the number is
  not interpretable — "0.71 similar" does not tell me what to go do, and a
  threshold change silently reshuffles everything. Still useful *inside*
  taxonomy maintenance, for suggesting which node an unmapped phrase belongs
  under.
- **LLM-generated taxonomy, auto-extended.** Very attractive: no maintenance,
  always current. Rejected because a vocabulary that changes underneath the
  scores destroys month-over-month comparability, which is most of the value.
  The `unmapped[]` review loop is the deliberate compromise — the corpus
  proposes, a human disposes.
- **An off-the-shelf ontology (ESCO, O*NET, LinkedIn skills).** Broad, stale
  at the resolution that matters, and organized around job titles rather than
  design competencies. `craft.python` and `design.systems.consistency` sitting
  at the same level would defeat the entire thesis.

## Consequences

- **Maintenance is required.** Roughly monthly, ~10 minutes, via
  `career taxonomy review`. If that stops happening, the taxonomy goes stale
  and the whole system degrades quietly. This is the single biggest
  operational risk in the design, and it is accepted knowingly.
- Recall is bounded by alias coverage. Mitigated by the unmapped loop, which
  makes gaps in coverage visible rather than silent.
- Renaming a slug is a breaking change requiring a `renames:` entry and a
  version bump.
- In exchange: every score decomposes to specific documents and quotes, and
  trends over time mean something.
