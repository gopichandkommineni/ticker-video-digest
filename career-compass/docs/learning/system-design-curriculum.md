# The repo as a system-design curriculum

The second stated purpose of this project is to be a system-design learning
exercise. This document makes that explicit: it maps the design problems this
system actually contains onto the canonical topics they mirror, so that
building each milestone *is* the studying.

The premise is that system-design competence is built by making decisions
under real constraints and then living with them — not by reading summaries of
other people's decisions. This repo is small enough to finish and real enough
to hurt when a decision is wrong. That combination is the point.

## How to use this

For each milestone in `docs/07-roadmap.md`:

1. **Before building:** read the "problem" column and write down your answer,
   with alternatives, *before* looking at the ADR. Ten minutes, in a scratch
   file.
2. **Build it.**
3. **After:** compare against the ADR. Where they differ, one of the two is
   wrong — figure out which, and if it's the ADR, supersede it. That
   disagreement is the highest-value moment in the whole loop.
4. **Then** read the "in the wild" column, which is where the same problem
   shows up at scale.

## The map

| Milestone | The problem you actually face | The canonical topic | Where it shows up in the wild |
|---|---|---|---|
| M1 Storage | Evolve a schema on a live single-file store with no downtime story; validate a foreign key whose source of truth is a YAML file | Schema design, migrations, referential integrity across system boundaries | Every migration framework; config-as-data systems (Kubernetes CRDs) |
| M2 Ingest | Fetch idempotently; never refetch what hasn't changed; store immutably so downstream is replayable | Content-addressed storage, idempotency, conditional requests, immutable logs | Git objects, Docker layers, S3 + ETags, CDN caching |
| M2 Ingest | One bad endpoint must not fail the run | Bulkheads, per-partition failure isolation, graceful degradation | Hystrix/resilience4j, service meshes, any crawler at scale |
| M3 Extract | An expensive, non-deterministic, improving transform over an append-only corpus | Materialized views, incremental vs. full recompute, cache invalidation | dbt models, feature stores, search index rebuilds |
| M3 Extract | Change a prompt without destroying the ability to tell whether it helped | Schema/artifact versioning, blue-green for data, backfills | ML model registries, A/B infrastructure, event-schema registries |
| M4 Jobs | Know that a posting *closed* when nothing ever told you it did | Inferring state transitions from repeated snapshots; absence as a signal; tombstones | Service discovery health checks, CRDT tombstones, reconciliation loops |
| M4 Jobs | Same logical entity, different URLs, changing text over time | Entity resolution, natural vs. surrogate keys, slowly-changing dimensions | CDC pipelines, MDM, warehouse dimension modelling |
| M5 Scoring | A score that a human must be able to argue with | Explainability, deterministic pipelines, separating policy (config) from mechanism (code) | Ranking systems, credit scoring, feature flags, policy engines (OPA) |
| M5 Scoring | Test a system whose "correct" output is a judgment call | Golden datasets, property-based invariants, regression fixtures | Recsys offline eval, compiler test suites, LLM evals |
| M6 Automation | Schedule by staleness rather than by clock | Work queues, lease/claim patterns, backpressure, control loops | Cron vs. reconciliation loops; Kubernetes controllers; crawler frontiers |
| M6 Automation | Exactly one writer to a store with no locking to speak of | Single-writer discipline, concurrency control, write-ahead logs | SQLite WAL, leader election, partitioned Kafka consumers |
| M7 Synthesis | Aggregate across small-N, high-variance data without inventing trends | Statistical significance, smoothing, confidence in rollups | Analytics dashboards, anomaly detection, A/B result reading |
| Cross-cutting | Add a company without writing code | Plugin architecture, dependency inversion, config-driven design | Terraform providers, Kubernetes operators, Datadog integrations |
| Cross-cutting | Two representations that must be compared but never can be, directly | Canonical data models, anti-corruption layers, ontology design | ETL conformed dimensions; DDD bounded contexts; FHIR, schema.org |

## The five ideas worth internalizing

If you take nothing else from building this, take these. Each has an ADR
behind it and each generalizes far past this repo.

**1. Separate what you *observed* from what you *concluded*.**
Raw store vs. derived tables (ADR-0002). Observations are precious and often
unrepeatable; conclusions are cheap and will be wrong. Systems that conflate
them cannot improve without re-observing, and re-observing is usually
impossible. This is the same instinct behind event sourcing, immutable data
lakes, and keeping your logs.

**2. Make the extension point match the shape of the world, not the shape of
your list.**
ATS adapters, not company adapters (ADR-0004). The number of job-board
platforms is a property of the market and grows slowly. The number of
companies I care about is a property of my ambition and grows fast. Build
against the slow-growing axis and the marginal cost of the fast-growing one
goes to zero.

**3. Two things that must be compared need a third thing to be compared
*in*.**
The skill taxonomy (ADR-0005). Resumes and job postings are both prose and
have no join key, so you invent one and project both sides into it. This is
the canonical data model / anti-corruption layer pattern, and once you see it
you see it everywhere: every integration platform, every warehouse, every
protocol.

**4. Policy in config, mechanism in code.**
The thesis of this entire project — design > craft — is seven numbers in
`config/scoring.yaml`. Being *wrong about the thesis* costs one edit and a
re-run, not a rewrite. Ask of any strong opinion in a system: if this is
wrong, what does it cost to find out? If the answer is "a rewrite," the
opinion is in the wrong layer.

**5. Silence is the dangerous failure.**
A dead job-board endpoint returns zero postings, which reads as "they aren't
hiring" — a confident, wrong, *actionable* answer. Hence `verified: false` by
default, consecutive-failure detection, auto-disable, and pinned annotations
that surface in the brief (ADR-0004). Design your failure modes to be loud.
Systems that fail quietly are worse than systems that fail.

## Companion reading

Pair each milestone with the corresponding material rather than reading a book
front to back:

- *Designing Data-Intensive Applications* — ch. 2–3 with M1, ch. 10–11 with
  M3, ch. 5 with M4's snapshot-reconciliation problem.
- *Database Internals* — with M1/M6 when the single-writer constraint starts
  to bite.
- Netflix, Reddit, and Nvidia's own engineering blogs — which this system is
  ingesting anyway. Reading them as a student of their *decisions* rather than
  their results is the highest-leverage version of the loop: it feeds both
  purposes of the repo at once.
- Any ADR collection published by a real company, read for the *rejected*
  alternatives.
