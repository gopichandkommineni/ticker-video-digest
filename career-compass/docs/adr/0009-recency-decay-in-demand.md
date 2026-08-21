# ADR-0009 — Demand decays with document age

**Status:** Accepted · 2026-08-21

## Context

Signal about a company is not equally valid over time.

A 2019 Netflix post describing a system they have since replaced is not weak
evidence about what they want today — it is *actively misleading*, and
naive counting would rank it identically to a posting opened last week.

Job postings age even faster. An open req is a live budget line; a req from
eighteen months ago says something about a team that may no longer exist.

But different kinds of signal age at genuinely different rates. Architecture
changes more slowly than headcount. A company's core technical domain barely
moves at all. So a single global decay constant would be wrong in both
directions at once.

## Decision

Every contribution to a demand score is multiplied by an exponential decay
term with a **half-life that depends on the source kind**:

```
decay(t) = 0.5 ** (age_days / half_life_days)
```

| Kind | Half-life | Reasoning |
|---|---|---|
| `job_posting` | 120d | Open reqs are live budget; stale ones mislead fast. |
| `blog_post` | 400d | Architecture changes slower than hiring. |
| `talk` | 400d | Same. |
| `oss` | 550d | Repo direction shifts slowly. |
| `note` (manual) | 240d | Human intel is high-value but perishable. |

Nothing is ever deleted or excluded — old documents keep contributing, just
less. This preserves the ability to ask "what did they care about in 2023?"
by re-running with decay disabled.

Two related corrections live alongside decay because they solve the same class
of problem — one loud source distorting the picture:

- **Distinct-source guard.** Demand is scaled by
  `min(1.0, 0.5 + 0.25 × distinct_source_count)`, so a theme appearing in one
  long blog post is halved until something else corroborates it.
- **Trend, not just level.** `company_skill_demand.trend` compares the current
  window against the previous one, which is often more actionable than the
  absolute score: a skill rising from 20 to 45 matters more than one flat at
  60.

All half-lives live in `config/scoring.yaml`.

## Alternatives considered

- **Hard cutoff window (e.g. last 12 months).** A cliff, so scores jump
  discontinuously as documents cross the boundary, and it throws away
  slow-moving architectural signal entirely.
- **No decay, count everything.** Companies with long blog archives
  systematically dominate, and the score describes their history rather than
  their present.
- **Linear decay.** Requires an arbitrary zero point and behaves worse at
  both ends than exponential.
- **One global half-life.** Simpler, and wrong for at least one source kind by
  construction.

## Consequences

- Scores drift downward for a company that stops publishing, which is correct
  but can read as "they stopped caring" when it means "they stopped writing."
  Postings are the corrective, since they decay fastest and are hardest to
  fake.
- Half-lives are guesses. They are config, they are documented, and they
  should be revisited once there is a year of data to check them against.
- Comparing scores across time requires recording the taxonomy version and
  extractor version alongside, or a config change looks like a real trend.
