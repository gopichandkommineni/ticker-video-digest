# 05 — Gap scoring

Deterministic, explainable, and tunable from `config/scoring.yaml`. No LLM
runs in this stage — the LLM's job ended when it produced `skill_mention`
rows. Everything below is arithmetic over those rows, so it is unit-testable
and it moves for reasons I can point at.

## Demand

How much does company *C* want skill *S*, right now?

```
demand(C, S) = branch_weight(S) × Σ over mentions m of S at C:
                   role_weight(m.role)
                 × level_weight(m.document.level_hint)
                 × source_weight(m.document.kind)
                 × m.weight
                 × decay(m.document.published_at)
```

then normalized to 0–100 across that company's skills, so companies with
verbose blogs are comparable to companies with terse ones.

**`decay`** — exponential with a half-life per source kind:

```
decay(t) = 0.5 ** (age_days / half_life_days)
```

| Source kind | Half-life | Reasoning |
|---|---|---|
| `job_posting` | 120d | An open req is a live budget line. Stale reqs mislead fast. |
| `blog_post` | 400d | Architecture changes slower than headcount. |
| `talk` | 400d | Same. |
| `oss` | 550d | Repos persist; direction shifts slowly. |
| `note` (manual) | 240d | Human intel is high-value but perishable. |

**`role_weight`** — is this a hiring bar or a description?

| Role | Weight | Meaning |
|---|---|---|
| `requirement` | 1.0 | "You must have…" — an actual bar |
| `nice_to_have` | 0.4 | "Bonus if…" |
| `described_system` | 0.6 | "We run…" — they do it, may not be hiring for it |
| `aspiration` | 0.5 | "We're moving toward…" — leading indicator, worth weight |

**`level_weight`** — set this to the level you are targeting; mentions at that
level count fully, adjacent levels count less. Default targets senior/staff.

**`distinct_source_count` guard.** A skill mentioned twelve times in one long
blog post is one data point, not twelve. Demand is multiplied by
`min(1.0, 0.5 + 0.25 × distinct_source_count)`, so a single-source theme is
halved until corroborated. This is the single most important correction in the
model — without it, whoever writes the longest blog post defines the industry.

## Supply

How much do I have of skill *S*?

```
supply(S) = 100 × sat( 0.35 × rating_component
                     + 0.50 × evidence_component
                     + 0.15 × recency_component )
```

- **`rating_component`** — `self_rating / 5`, from `profile/resume.yaml`.
  **Capped at 0.4 when there are zero evidence rows.** Self-assessment without
  an artifact is not supply; it is optimism.
- **`evidence_component`** — a saturating function of evidence, weighted by
  kind and by whether the entry carries an `impact_metric`:

  | Evidence kind | Weight | Why |
  |---|---|---|
  | `system` (shipped, owned) | 1.0 | The strongest claim available |
  | `design_doc` | 0.9 | Directly demonstrates design competency |
  | `incident` (led response/postmortem) | 0.8 | Judgment under pressure |
  | `writing` / `talk` | 0.7 | Public, checkable |
  | `pr` | 0.5 | Narrow scope |
  | `course` | 0.2 | Exposure, not evidence |

  An entry with a concrete `impact_metric` ("cut p99 from 900ms to 120ms
  across 40M daily requests") gets ×1.3. Numbers are what survive an
  interview.
- **`recency_component`** — `0.5 ** (years_since_last_used / 4)`. Skills
  decay. Distributed systems work from 2015 is worth roughly a quarter of the
  same work from 2023.

## Gap and leverage

```
gap(C, S)      = demand(C, S) × (1 − supply(S) / 100)
leverage(C, S) = gap(C, S) × closability(S)
```

**`gap`** is "how much this hurts". **`leverage`** is "what to actually do
next", and that distinction is the point of the whole system. A gap you cannot
close in the time you have is not a task, it is a fact about the world.

`closability` is a per-branch prior in `config/scoring.yaml`, overridable
per-skill:

| Branch | Closability | Reasoning |
|---|---|---|
| `craft` | 0.9 | Learn a language in weeks. |
| `platform` | 0.7 | Hands-on in a side project. |
| `ai` | 0.7 | Fast-moving, buildable. |
| `design.systems` | 0.5 | Needs a real system with real constraints. |
| `design.product` | 0.4 | Needs users and consequences. |
| `domain` | 0.3 | Needs to be *in* the domain. |
| `design.org` | 0.2 | Needs an org and years. |

The consequence is intentional and slightly uncomfortable: `domain.video` will
show a large gap for Netflix and a low leverage. The system's honest advice is
"you will not close this by studying — either get adjacent to it or lead with
something else," which is more useful than a study plan that cannot work.

## Prep plan

The top *N* leverage rows become `prep_item`s, keyed by evidence type — the
plan targets the **weakest component** of supply, not the skill in general:

| Situation | Generated action kind |
|---|---|
| High rating, no evidence | `write` or `talk` — make the existing work legible |
| Low rating, high closability | `build` — a project that forces the constraint |
| Stale (last used > 4y) | `build` small + `write` — refresh and re-evidence |
| Domain gap, low closability | `read` + `talk_to` — vocabulary and a person inside |

Each item carries the `gap_id`, so I can always ask "why is this on my list?"
and get back the specific postings and posts that put it there.

## Anti-goals in scoring

- **No single blended "Netflix readiness: 73%" score.** It would be
  false precision and I would optimize the number instead of the career.
  Output is always a ranked list with rationale.
- **No LLM in the loop here.** Scores must move only when data or config
  moves.
- **No hidden constants.** Every number above lives in `config/scoring.yaml`.
  If a score surprises me, I should be able to find the line that caused it.
