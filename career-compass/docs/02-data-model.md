# 02 — Data model

SQLite, one file: `data/career.db`. Schema lives in
`src/career_compass/store/schema.sql`; migrations are numbered, forward-only
files in `src/career_compass/store/migrations/`.

Four zones, in dependency order:

```
 provenance   →   canonical   →   derived   →   me
 ──────────       ─────────       ───────       ──
 run             company         extraction    profile_claim
 source          raw_document    skill_mention evidence
                 document        company_skill_demand
                 job_posting     gap
                 skill           prep_item
                 annotation
```

Only the **derived** zone is disposable. `DELETE FROM extraction;` followed by
a re-run must reproduce the same state from provenance + canonical + `profile/`.
That invariant is the point of the whole layout (ADR-0002).

## Provenance

### `run`
| column | type | notes |
|---|---|---|
| `id` | INTEGER PK | |
| `job_name` | TEXT | `ingest`, `normalize`, `extract`, `analyze` |
| `started_at` / `finished_at` | TEXT (ISO-8601 UTC) | |
| `status` | TEXT | `running` / `ok` / `partial` / `failed` |
| `stats_json` | TEXT | counts, per-source outcomes, errors |

Answers "why did last Tuesday's brief look thin?" without guessing.

### `source`
| column | type | notes |
|---|---|---|
| `id` | INTEGER PK | |
| `company_id` | FK → company | |
| `kind` | TEXT | `blog` / `jobs` / `talk` / `oss` / `news` / `manual` |
| `adapter` | TEXT | `rss`, `ats.greenhouse`, `ats.workday`, `manual.inbox`, … |
| `config_json` | TEXT | adapter parameters (board slug, feed URL, tenant) |
| `enabled` | INTEGER | |
| `refresh_interval_hours` | INTEGER | drives "what is due" |
| `last_run_at` / `last_ok_at` | TEXT | consecutive-failure detection |
| `verified` | INTEGER | has a human confirmed this endpoint is real? |

Sources are **seeded from `config/sources.yaml`**, which is the editable
source of truth. The table is a materialized copy carrying runtime state.

## Canonical

### `company`
`id`, `slug` (UNIQUE, e.g. `netflix`), `name`, `priority` (1 = actively
targeting), `status` (`target` / `watching` / `parked`), `notes`.

Deliberately thin. Everything about *how* to fetch from a company lives in
`source`; everything *learned* lives in derived tables.

### `raw_document`
| column | notes |
|---|---|
| `id` | INTEGER PK |
| `source_id` | FK → source |
| `content_hash` | TEXT, sha256 of the payload — **UNIQUE** |
| `url` | fetch URL (may be null for manual) |
| `fetched_at`, `http_status`, `content_type`, `byte_size` | |
| `payload_path` | `data/raw/ab/abcd…json` |

`content_hash` UNIQUE is the dedupe mechanism (ADR-0002). Re-fetching an
unchanged posting is an `INSERT OR IGNORE` — a no-op, and cheap.

### `document`
The common shape everything normalizes into.

| column | notes |
|---|---|
| `id` | INTEGER PK |
| `raw_document_id` | FK → raw_document |
| `company_id` | FK → company |
| `kind` | `blog_post` / `job_posting` / `talk` / `repo` / `note` |
| `external_id` | stable id from the source, when it has one |
| `title`, `url`, `author`, `lang` | |
| `published_at` | source's timestamp; falls back to `first_seen_at` |
| `body_text` | plain text, markup stripped |
| `first_seen_at`, `last_seen_at` | last_seen drives closure inference |
| `supersedes_document_id` | previous version when content changed |

`(company_id, kind, external_id)` is UNIQUE where `external_id` is non-null.
An edited JD becomes a **new** `document` row pointing back at the old one via
`supersedes_document_id`, so requirement drift is queryable.

### `job_posting`
One row per document of kind `job_posting`. `document_id` PK/FK, plus
`req_id`, `title`, `team`, `location`, `remote_ok`, `level_hint`
(`junior`/`mid`/`senior`/`staff`/`principal`, parsed from the title — nullable
and often wrong, so treat it as a weak prior), `employment_type`, `posted_at`,
`last_seen_at`, `status` (`open` / `presumed_closed`).

**Closure is inferred, not fetched.** A posting absent from two consecutive
successful runs of its source becomes `presumed_closed`. Two runs, not one,
because a single flaky fetch must not close a hiring req. *Time-to-close is
signal*: reqs that close in nine days are the roles they are desperate for.

### `skill`
The controlled vocabulary — the join key between what companies want and what
I have (ADR-0005).

`id`, `slug` (UNIQUE, dotted: `design.systems.consistency`), `name`,
`category` (top-level branch), `parent_id` (self-FK, a tree), `aliases_json`
(surface forms: `"eventual consistency"`, `"CRDT"`, `"quorum reads"`),
`description`, `is_active`.

Seeded from `taxonomy/skills.yaml`, which is the editable source of truth.

### `annotation`
`id`, `entity_type`, `entity_id`, `body`, `created_at`, `pinned`.

A polymorphic sticky note attachable to any row: a company, a posting, a
skill, a gap. This is where "a friend says this team is actually a rewrite in
disguise" lives. Analysis reads pinned annotations and surfaces them verbatim
in briefs — never summarized away (ADR-0006).

## Derived

### `extraction`
| column | notes |
|---|---|
| `id`, `document_id` | |
| `extractor_version` | e.g. `doc-v3` — bump on prompt change |
| `model`, `schema_version` | |
| `payload_json` | the validated pydantic model, serialized |
| `input_tokens`, `output_tokens`, `cost_usd` | budget visibility |
| `created_at` | |

UNIQUE `(document_id, extractor_version, schema_version)`. Old rows are kept,
so a new prompt can be A/B'd against the old on the same corpus before
becoming the default. Analysis reads only the version pinned in
`config/scoring.yaml` (ADR-0007).

### `skill_mention`
`id`, `extraction_id`, `skill_id`, `weight` (0–1, how central to the
document), `context_quote` (verbatim), `role` (`requirement` /
`nice_to_have` / `described_system` / `aspiration`).

The `role` column matters: "we run Cassandra" and "you must have designed a
Cassandra-scale store" are different claims, and only the second is a hiring
bar.

### `company_skill_demand`
Materialized rollup: `company_id`, `skill_id`, `window_days`, `score`,
`evidence_count`, `distinct_source_count`, `trend` (vs. previous window),
`computed_at`.

Recomputed wholesale each run — a small table, and full recompute is simpler
and less bug-prone than incremental (ADR-0009). `distinct_source_count` guards
against one verbose blog post inflating a theme.

### `gap`
`company_id`, `skill_id`, `demand_score`, `supply_score`, `gap_score`,
`leverage`, `rationale_json` (the document ids that drove it), `computed_at`.

`rationale_json` is non-negotiable: a career decision made on an unexplainable
number is worse than no number.

### `prep_item`
`id`, `gap_id`, `action`, `kind` (`build` / `read` / `write` / `practice` /
`talk_to`), `effort_hours`, `resource_url`, `status`, `due_at`,
`completed_at`, `notes`. The only table I edit by hand day-to-day.

## Me

### `profile_claim` / `evidence`
Materialized from `profile/resume.yaml` on load; the YAML is the source of
truth (ADR-0008).

`profile_claim`: `skill_id`, `self_rating` (1–5), `last_used_year`,
`notes`.

`evidence`: `profile_claim_id`, `kind` (`system` / `pr` / `design_doc` /
`incident` / `talk` / `writing` / `course`), `title`, `description`,
`impact_metric`, `url`, `date`, `confidence`.

The split is the heart of the supply side. A claim with a 5 self-rating and
zero evidence rows scores **low**, and the gap report says so in those words:
*"You rate yourself 5 on distributed consistency and have no artifact to point
at. That is an interview failure, not a skill gap."*

## Indexes

```sql
CREATE UNIQUE INDEX ux_raw_hash        ON raw_document(content_hash);
CREATE INDEX        ix_doc_company_pub ON document(company_id, published_at DESC);
CREATE UNIQUE INDEX ux_doc_external    ON document(company_id, kind, external_id)
                                        WHERE external_id IS NOT NULL;
CREATE INDEX        ix_mention_skill   ON skill_mention(skill_id);
CREATE INDEX        ix_demand_lookup   ON company_skill_demand(company_id, score DESC);
CREATE INDEX        ix_job_status      ON job_posting(status, last_seen_at);
```

Small dataset; these exist for query clarity as much as speed.
