# 07 — Roadmap

Sequenced so that **something useful exists after every milestone**, and so
each milestone forces one system-design problem to be solved for real (see
`docs/learning/system-design-curriculum.md`).

## M0 — Design (this milestone) ✅

Architecture, data model, contracts, taxonomy, scoring model, ADRs, typed
stubs. No behavior.

*Exit:* I can explain the whole system from `docs/` without reading code, and
disagree with specific decisions before they cost anything.

---

## M1 — Storage + profile

- `schema.sql` and the migration runner.
- Loaders: `companies.yaml`, `sources.yaml`, `skills.yaml`, `resume.yaml` →
  tables, with validation that fails loudly on a bad slug.
- `career profile show` — renders my claims and evidence, flags every claim
  with zero evidence.

*Exit:* `career profile show` produces a real, uncomfortable list of
unevidenced claims. **This is already useful with zero companies ingested** —
which is why it comes first.

*Design problem:* schema migration on a live single-file store; validating a
foreign key that lives in YAML.

---

## M2 — One vertical slice: Netflix blog

- `rss` adapter, `FetchContext` with robots + rate limiting, raw store,
  run ledger.
- `normalize` for feed entries.
- No LLM yet — just documents in a table.

*Exit:* `career docs --company netflix` lists their recent engineering posts
with full text stored locally.

*Design problem:* content-addressed storage; idempotent fetch; conditional
requests.

---

## M3 — Extraction

- Per-document extraction with a pydantic schema, taxonomy in a cached system
  prompt, `unmapped[]` collection.
- Deterministic alias pre-pass as a baseline to check the model against.
- `extraction` versioning and cost accounting.
- `career taxonomy review`.

*Exit:* `career themes --company netflix` gives a ranked, quote-backed list of
what they've been writing about.

*Design problem:* schema-versioned derived data; idempotent expensive
operations; prompt caching economics.

---

## M4 — Jobs

- `ats.greenhouse` (simplest public API) → then `ats.eightfold`,
  `ats.workday`.
- `job_posting`, closure inference, requirement-diff between versions.
- `career sources verify`.

*Exit:* All four target companies' open senior roles in one table, with
`opened_at` / `presumed_closed_at`.

*Design problem:* inferring state transitions from repeated snapshots without
a change feed — the "how do you know it's gone?" problem.

---

## M5 — Scoring

- `demand`, `supply`, `gap`, `leverage` as pure functions with a real test
  suite over fixtures.
- `career gaps`, `career plan`.
- `config/overrides.yaml`.

*Exit:* A ranked, explainable prep plan for Netflix that I actually act on.

*Design problem:* explainable scoring; keeping config and code separable;
testing a model whose "correctness" is a judgment call.

---

## M6 — Automation + surfaces

- GitHub Actions daily job (ADR-0010), committing the DB back.
- `career diff --since 7d`; weekly digest written to `briefs/`.
- Streamlit dashboard over the same queries.

*Exit:* I stop running commands and start reading Monday's brief.

*Design problem:* scheduling by staleness rather than cron; safe automated
commits to a version-controlled database.

---

## M7 — Cross-company synthesis

- "Themes rising at 3+ companies simultaneously" — the industry-level signal
  that no single company's data shows.
- Company similarity by demand vector; "who else wants what Netflix wants"
  finds targets I hadn't considered.
- Time series: is `ai.evals` demand at Google rising or flat?

*Exit:* The system tells me something I did not already believe.

*Design problem:* rollups across a small-N, high-variance dataset without
over-reading noise.

---

## Later / maybe

- Application + conversation tracking (ADR: probably a separate tool).
- Interview-question generation grounded in *their* actual systems.
- Talk/podcast transcript ingestion.
- Embedding-assisted alias suggestion in `taxonomy review`.
- Recruiter-message triage.

## Explicitly deferred, with reasons

| Idea | Deferred because |
|---|---|
| Postgres | The dataset is thousands of rows (ADR-0003). |
| Vector DB / RAG | The taxonomy exists so this is countable, not retrieved (ADR-0005). |
| Web UI before CLI | The CLI is the fastest way to find out the scoring is wrong. |
| More companies before M5 | Four companies with a working loop beats forty with none. |
| Auto-updating the taxonomy | Kills month-over-month comparability (ADR-0005). |
