# ADR-0001 — Record architecture decisions

**Status:** Accepted · 2026-08-21

## Context

This repo has two purposes. The first is to answer career questions. The
second, stated up front, is to be a system-design learning exercise.

The second purpose is only served if the *reasoning* survives. A finished
system teaches very little: every remaining line looks inevitable, and the
three alternatives that were considered and rejected — which is where all the
actual learning is — have vanished. Six months from now I will not remember
why the raw store is content-addressed, and I will be tempted to "simplify" it.

## Decision

Every non-obvious decision gets an ADR in `docs/adr/`, numbered, with:
context, decision, **alternatives considered and why they lost**, and
consequences including the costs being accepted.

ADRs are immutable. A changed decision is a new ADR that supersedes the old
one; the superseded file stays.

## Alternatives considered

- **Comments in code.** Rot, scatter, and cannot hold a rejected alternative
  without being confusing.
- **A single DESIGN.md.** Becomes a wall nobody re-reads, and edits erase the
  history of thinking, which is the asset.
- **Nothing; it's a personal repo.** This is exactly the reasoning that makes
  personal repos unmaintainable after a three-month gap. And it forfeits
  purpose two entirely.

## Consequences

- Some friction per decision. Accepted — the friction is the thinking.
- The ADR list doubles as an index of the system-design topics this project
  actually touched, which feeds
  `docs/learning/system-design-curriculum.md`.
- Bad decisions stay visible. That is the point.
