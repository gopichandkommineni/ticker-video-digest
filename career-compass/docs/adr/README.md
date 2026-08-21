# Architecture Decision Records

One file per decision that was not obvious. Each records the context, the
choice, the alternatives that lost, and the consequences — including the bad
ones.

An ADR is immutable once accepted. If a decision changes, write a new ADR that
supersedes it; the wrong turn is part of the record and is usually the most
instructive part.

| # | Decision | Status |
|---|---|---|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | Accepted |
| [0002](0002-raw-canonical-split.md) | Immutable raw store, replayable derivation | Accepted |
| [0003](0003-sqlite-as-canonical-store.md) | SQLite as the canonical store | Accepted |
| [0004](0004-ats-adapters-not-company-adapters.md) | Adapters per ATS platform, not per company | Accepted |
| [0005](0005-controlled-taxonomy-as-join-key.md) | A hand-curated skill taxonomy is the join key | Accepted |
| [0006](0006-manual-input-is-an-adapter.md) | Manual input is an adapter, not an exception | Accepted |
| [0007](0007-versioned-llm-extractions.md) | LLM extractions are versioned and additive | Accepted |
| [0008](0008-evidence-backed-profile.md) | Profile claims require evidence to score | Accepted |
| [0009](0009-recency-decay-in-demand.md) | Demand decays with document age | Accepted |
| [0010](0010-github-actions-as-scheduler.md) | GitHub Actions is the scheduler | Accepted |
