-- Career Compass canonical schema. See docs/02-data-model.md.
--
-- Four zones: provenance, canonical, derived, me.
-- Only DERIVED is disposable: dropping it and re-running must reproduce
-- identical state with zero network calls (ADR-0002).
--
-- DESIGN PHASE: this is the intended shape, not yet exercised by code.
-- Migrations live in store/migrations/ and are forward-only.

PRAGMA foreign_keys = ON;

-- ══ provenance ═══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS run (
    id           INTEGER PRIMARY KEY,
    job_name     TEXT NOT NULL,
    started_at   TEXT NOT NULL,
    finished_at  TEXT,
    status       TEXT NOT NULL CHECK (status IN ('running','ok','partial','failed')),
    stats_json   TEXT
);

CREATE TABLE IF NOT EXISTS source (
    id                     INTEGER PRIMARY KEY,
    company_id             INTEGER REFERENCES company(id),
    kind                   TEXT NOT NULL,
    adapter                TEXT NOT NULL,
    config_json            TEXT NOT NULL,
    enabled                INTEGER NOT NULL DEFAULT 1,
    -- Unverified sources are ingested but EXCLUDED from analysis. A silently
    -- dead endpoint reads as "they aren't hiring" (ADR-0004).
    verified               INTEGER NOT NULL DEFAULT 0,
    refresh_interval_hours INTEGER NOT NULL DEFAULT 24,
    last_run_at            TEXT,
    last_ok_at             TEXT,
    consecutive_failures   INTEGER NOT NULL DEFAULT 0
);

-- ══ canonical ════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS company (
    id       INTEGER PRIMARY KEY,
    slug     TEXT NOT NULL UNIQUE,
    name     TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 3,
    status   TEXT NOT NULL DEFAULT 'watching',
    why      TEXT
);

CREATE TABLE IF NOT EXISTS raw_document (
    id           INTEGER PRIMARY KEY,
    source_id    INTEGER NOT NULL REFERENCES source(id),
    content_hash TEXT NOT NULL UNIQUE,   -- dedupe + change detection
    url          TEXT,
    fetched_at   TEXT NOT NULL,
    http_status  INTEGER,
    content_type TEXT,
    byte_size    INTEGER,
    payload_path TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS document (
    id                      INTEGER PRIMARY KEY,
    raw_document_id         INTEGER NOT NULL REFERENCES raw_document(id),
    company_id              INTEGER NOT NULL REFERENCES company(id),
    kind                    TEXT NOT NULL,
    external_id             TEXT,
    title                   TEXT NOT NULL,
    url                     TEXT,
    author                  TEXT,
    lang                    TEXT DEFAULT 'en',
    published_at            TEXT,
    body_text               TEXT NOT NULL,
    first_seen_at           TEXT NOT NULL,
    last_seen_at            TEXT NOT NULL,
    -- An edited JD is a NEW row pointing back, so requirement drift is
    -- queryable rather than lost.
    supersedes_document_id  INTEGER REFERENCES document(id)
);

CREATE TABLE IF NOT EXISTS job_posting (
    document_id     INTEGER PRIMARY KEY REFERENCES document(id),
    req_id          TEXT,
    team            TEXT,
    location        TEXT,
    remote_ok       INTEGER,
    level_hint      TEXT DEFAULT 'unknown',  -- weak prior; often wrong
    employment_type TEXT,
    posted_at       TEXT,
    last_seen_at    TEXT,
    -- Closure is INFERRED from absence across two consecutive successful runs.
    -- Two, not one: a flaky fetch must never close a req.
    status          TEXT NOT NULL DEFAULT 'open',
    closed_at       TEXT
);

CREATE TABLE IF NOT EXISTS skill (
    id          INTEGER PRIMARY KEY,
    slug        TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    category    TEXT NOT NULL,
    parent_id   INTEGER REFERENCES skill(id),
    aliases_json TEXT,
    description TEXT,
    is_active   INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS annotation (
    id          INTEGER PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id   INTEGER NOT NULL,
    body        TEXT NOT NULL,
    pinned      INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL
);

-- ══ derived (disposable) ═════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS extraction (
    id                INTEGER PRIMARY KEY,
    document_id       INTEGER NOT NULL REFERENCES document(id),
    extractor_version TEXT NOT NULL,
    schema_version    INTEGER NOT NULL,
    model             TEXT NOT NULL,
    payload_json      TEXT NOT NULL,
    input_tokens      INTEGER,
    output_tokens     INTEGER,
    cost_usd          REAL,
    created_at        TEXT NOT NULL,
    -- Additive, never updated in place: a prompt change is an experiment
    -- runnable alongside the old one, not a migration (ADR-0007).
    UNIQUE (document_id, extractor_version, schema_version)
);

CREATE TABLE IF NOT EXISTS skill_mention (
    id            INTEGER PRIMARY KEY,
    extraction_id INTEGER NOT NULL REFERENCES extraction(id),
    skill_id      INTEGER NOT NULL REFERENCES skill(id),
    role          TEXT NOT NULL,
    weight        REAL NOT NULL,
    context_quote TEXT NOT NULL   -- never null: every score must decompose to text
);

CREATE TABLE IF NOT EXISTS unmapped_phrase (
    id            INTEGER PRIMARY KEY,
    extraction_id INTEGER NOT NULL REFERENCES extraction(id),
    phrase        TEXT NOT NULL,
    context_quote TEXT,
    suggested_parent TEXT
);

CREATE TABLE IF NOT EXISTS company_skill_demand (
    company_id           INTEGER NOT NULL REFERENCES company(id),
    skill_id             INTEGER NOT NULL REFERENCES skill(id),
    window_days          INTEGER NOT NULL,
    score                REAL NOT NULL,
    evidence_count       INTEGER NOT NULL,
    distinct_source_count INTEGER NOT NULL,
    trend                REAL,
    computed_at          TEXT NOT NULL,
    PRIMARY KEY (company_id, skill_id, window_days)
);

CREATE TABLE IF NOT EXISTS gap (
    id            INTEGER PRIMARY KEY,
    company_id    INTEGER NOT NULL REFERENCES company(id),
    skill_id      INTEGER NOT NULL REFERENCES skill(id),
    demand_score  REAL NOT NULL,
    supply_score  REAL NOT NULL,
    gap_score     REAL NOT NULL,
    leverage      REAL NOT NULL,
    rationale_json TEXT NOT NULL,   -- non-negotiable
    suppressed    INTEGER NOT NULL DEFAULT 0,
    suppress_reason TEXT,
    computed_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS prep_item (
    id            INTEGER PRIMARY KEY,
    gap_id        INTEGER REFERENCES gap(id),
    action        TEXT NOT NULL,
    kind          TEXT NOT NULL,
    effort_hours  REAL,
    resource_url  TEXT,
    status        TEXT NOT NULL DEFAULT 'todo',
    due_at        TEXT,
    completed_at  TEXT,
    notes         TEXT
);

-- ══ me ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS profile_claim (
    id             INTEGER PRIMARY KEY,
    skill_id       INTEGER NOT NULL REFERENCES skill(id) UNIQUE,
    self_rating    INTEGER NOT NULL CHECK (self_rating BETWEEN 1 AND 5),
    last_used_year INTEGER,
    notes          TEXT
);

CREATE TABLE IF NOT EXISTS evidence (
    id               INTEGER PRIMARY KEY,
    profile_claim_id INTEGER NOT NULL REFERENCES profile_claim(id),
    kind             TEXT NOT NULL,
    title            TEXT NOT NULL,
    description      TEXT,
    impact_metric    TEXT,        -- 1.3x multiplier; numbers survive interviews
    url              TEXT,
    date             TEXT,
    confidence       TEXT DEFAULT 'medium'
);

-- ══ indexes ══════════════════════════════════════════════════════════════
CREATE INDEX IF NOT EXISTS ix_doc_company_pub ON document(company_id, published_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS ux_doc_external
    ON document(company_id, kind, external_id) WHERE external_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_mention_skill   ON skill_mention(skill_id);
CREATE INDEX IF NOT EXISTS ix_demand_lookup   ON company_skill_demand(company_id, score DESC);
CREATE INDEX IF NOT EXISTS ix_job_status      ON job_posting(status, last_seen_at);
CREATE INDEX IF NOT EXISTS ix_annotation      ON annotation(entity_type, entity_id);
