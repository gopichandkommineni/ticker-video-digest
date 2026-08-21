# 04 — The skill taxonomy

This is the crux of the system. Everything else is plumbing.

## The problem it solves

A job posting says *"experience with eventually consistent data stores at
scale."* My resume says *"built a multi-region inventory service using DynamoDB
global tables."* A human sees the match instantly. Naive string matching sees
nothing. And an LLM asked "does this resume match this JD?" gives a fluent,
confident, **unstable** answer — ask twice, get two different emphases, and
there is no way to say "this got worse since last month."

So the two sides never compare directly. Both project into a **shared,
hand-curated, versioned vocabulary**, and the comparison happens in that space
(ADR-0005).

```
   job posting ──LLM──▶ ┌──────────────┐ ◀──LLM(assisted)── resume.yaml
   blog post   ──LLM──▶ │  skill slug  │ ◀──hand-mapped──── evidence
                        └──────┬───────┘
                               │ deterministic
                               ▼
                     demand vs. supply vs. gap
```

Three properties follow:
- **Countable.** "Netflix mentioned `design.systems.consistency` in 6 of 11
  senior postings" is a fact, not a vibe.
- **Diffable.** Scores move month over month for legible reasons.
- **Debuggable.** Every score decomposes to specific documents and quotes.

## Shape

A tree, dotted slugs, in `taxonomy/skills.yaml`. Seven top-level branches:

| Branch | What lives here | Default weight |
|---|---|---|
| `design.systems` | Distributed systems, data modelling, API design, scaling, reliability | **1.0** |
| `design.product` | Problem framing, requirements, tradeoff articulation, prioritization | **0.9** |
| `design.org` | Technical leadership, RFC culture, cross-team design, mentorship | **0.8** |
| `ai` | LLM systems, evals, retrieval, agents, ML infrastructure | **0.8** |
| `domain` | Company-shaped knowledge: video, recsys, ads, GPU, social graph | **0.7** |
| `platform` | Cloud, orchestration, data infra, observability | **0.5** |
| `craft` | Languages, frameworks, libraries, tools | **0.3** |

Those weights encode the thesis in `docs/00-vision.md`: a Rust mention counts,
but a third as much as a consistency-model mention. **They live in
`config/scoring.yaml`, not in the taxonomy** — the vocabulary describes the
world, the weights describe my bet about it. Change your mind about the bet,
change one number, re-run `career analyze`, and the whole history rescores.

## Depth

Three levels, no deeper:

```
design.systems                       # branch
design.systems.consistency           # skill  ← scoring happens here
design.systems.consistency.crdt      # leaf   ← evidence attaches here
```

Level 2 is the scoring unit. Level 3 exists so a specific artifact can be
precise without fragmenting the score. Going deeper produces a vocabulary too
fine to accumulate counts and too tedious to maintain.

## Aliases do the real work

Each node carries an `aliases` list — the surface forms that actually appear
in the wild:

```yaml
- slug: design.systems.consistency
  name: Consistency & coordination
  aliases:
    - eventual consistency
    - strong consistency
    - linearizability
    - quorum
    - CRDT
    - distributed transaction
    - two-phase commit
    - consensus
    - Raft
    - Paxos
```

Aliases are fed to the extractor as part of the (prompt-cached) system block.
They are also a cheap deterministic pre-pass: exact alias hits are recorded
before the LLM is called, which both grounds the model and gives a
non-LLM baseline to check its output against.

## The `unmapped` loop

The extractor may **only** emit slugs that exist in the taxonomy. Anything it
cannot place goes into `unmapped[]` with a quote and a suggested parent.

`career taxonomy review` then shows the frequency-ranked backlog:

```
unmapped phrases, last 30 days
  17×  "chaos engineering"        suggests → design.systems.reliability
  11×  "eBPF"                     suggests → platform.observability
   9×  "media encoding pipeline"  suggests → domain.video
   4×  "vibe coding"              suggests → (none)
```

I decide: add as a leaf, add as an alias, or ignore. **The taxonomy is
maintained by me, informed by the corpus** — never silently extended by a
model. This is the guardrail that keeps the vocabulary stable enough for
month-over-month comparison, and it is also the mechanism by which the system
tells me the industry moved.

## Versioning

`taxonomy/skills.yaml` carries a top-level `version`. Adding a skill or an
alias is a **minor** bump; renaming or removing a slug is **major** and
requires a mapping entry:

```yaml
renames:
  - from: platform.k8s
    to: platform.orchestration
    version: 2.0
```

Analysis records the taxonomy version alongside each computed score, so a
chart that steps in March is explainable rather than mysterious.

## Levelling

Skills are not the whole story: *depth* matters, and the same slug means
different things at different levels. Rather than a second taxonomy, each
`skill_mention` carries a `role`, and each posting carries a `level_hint`:

- `requirement` in a staff-level posting → highest demand weight
- `requirement` in a mid-level posting → moderate
- `described_system` in a blog post → they do this, but may not be hiring for it
- `nice_to_have` → weakest

This keeps one vocabulary while letting the same slug carry different weight
depending on where it showed up. See `docs/05-gap-scoring.md`.
