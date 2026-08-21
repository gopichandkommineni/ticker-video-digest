# ADR-0008 — Profile claims require evidence to score

**Status:** Accepted · 2026-08-21

## Context

The supply side of the gap calculation is my own skill profile. The easy
implementation is a self-rating: a list of skills, each 1–5.

Self-ratings are a poor input for two independent reasons.

First, they are **uncalibrated** — not out of dishonesty, but because
confidence tracks familiarity, not depth, and the Dunning-Kruger shape is real
in exactly this domain.

Second, and more importantly: **an interview does not test what I know, it
tests what I can demonstrate.** "I understand distributed consistency" and "I
can walk you through the multi-region reconciliation system I designed, why we
chose read-repair over strict quorum, and what broke" are entirely different
assets. Only the second one gets an offer.

A gap report built on self-ratings would systematically under-report the
things that actually cost me offers.

## Decision

The profile is a two-level structure, hand-maintained in
`profile/resume.yaml`, which is the sole source of truth (nothing writes to
it).

- **`profile_claim`** — a skill, a self-rating, when it was last used.
- **`evidence`** — zero or more artifacts backing that claim: a system I
  owned, a design doc, an incident I led, a talk, writing, a PR, a course.
  Each with a description and, ideally, an `impact_metric`.

Scoring (see `docs/05-gap-scoring.md`) weights evidence at 0.50 and
self-rating at 0.35, and — the load-bearing rule — **caps the self-rating
contribution at 0.4 when there are zero evidence rows.**

The consequence is deliberate. A claim rated 5 with no evidence produces:

> *"You rate yourself 5 on distributed consistency and have no artifact to
> point at. That is an interview failure, not a skill gap."*

The generated prep item for that row is `write` or `talk`, not `build` —
because the work is already done and the problem is that it is illegible.
That distinction is one of the most useful things this system can produce, and
it is only possible because supply is decomposed rather than scalar.

Evidence kinds are weighted by how well they survive scrutiny: a shipped
system I owned (1.0) beats a design doc (0.9) beats a merged PR (0.5) beats a
completed course (0.2). Entries with a concrete `impact_metric` get ×1.3,
because numbers are what survive an interview.

## Alternatives considered

- **Self-ratings only.** Uncalibrated, and blind to the demonstrability gap
  that this system exists to find.
- **Parse the resume PDF automatically.** Tempting and it would be less work,
  but a resume is already a compressed, audience-tuned artifact. The evidence
  ledger is meant to hold *more* than the resume — the things that did not fit
  on two pages are frequently the strongest material.
- **Infer supply from GitHub activity.** Measures public code volume, which
  correlates weakly with design competency and not at all with work done
  inside a company.

## Consequences

- The profile takes real effort to fill in, and stays a manual quarterly
  chore. Accepted: the effort *is* the exercise. Writing out the evidence for
  a claim is most of the interview prep.
- Recent work is over-weighted relative to a long career. Partly intended
  (recency decay, ADR-0009), partly a known bias to watch.
- Honest low ratings produce large gaps and a discouraging report. The
  `leverage` ranking exists partly to keep the output actionable rather than
  merely accurate.
