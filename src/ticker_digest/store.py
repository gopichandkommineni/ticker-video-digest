"""SQLite storage for digest runs, tracked claims and generated threads.

This is what makes novelty detection possible: a claim is only "news" relative
to what we already stored, so every run writes its claims back with the date
they were first seen. Threads are stored whole — the thread *is* the
deliverable, and re-reading it should never require re-running the pipeline.

The ledger is split in two. ``claims`` is identity: one row per distinct claim
per ticker, carrying the novelty verdict and the date it was first heard.
``claim_citations`` is evidence: one row per video that made the claim, with
the channel that published it. Counting distinct channels there is what tells
a genuinely corroborated claim from one commentator saying it three times.

Lives in its own database (``data/digests.db``, overridable with
``TICKER_DIGEST_DB``) rather than the dashboard's ``snapshots.db``: different
lifecycle, different refresh job, and it must never be committed.
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from core.config import DIGEST_DB_PATH, NOVELTY_LOOKBACK_DAYS
from core.models import Citation, Claim, DigestRun, InsightThread

log = logging.getLogger(__name__)

# Bumped when the shape below changes. init_db migrates in place; there is no
# script for the user to remember to run.
SCHEMA_VERSION = 2

# Written for citations recovered from a v1 database, which predates channel
# tracking. Treated as "we don't know", never as a real channel.
UNKNOWN_CHANNEL = ""

_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS digest_runs (
    run_id        TEXT    PRIMARY KEY,
    ticker        TEXT    NOT NULL,
    company_name  TEXT    NOT NULL,
    source_kind   TEXT    NOT NULL,
    source_label  TEXT    NOT NULL,
    generated_at  TEXT    NOT NULL,
    video_count   INTEGER NOT NULL,
    payload_json  TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_runs_ticker ON digest_runs (ticker, generated_at);

-- Identity. first_seen_at is never overwritten: that column is the whole
-- point of the table. last_seen_at moves every time the claim comes up again.
CREATE TABLE IF NOT EXISTS claims (
    ticker            TEXT NOT NULL,
    fingerprint       TEXT NOT NULL,
    kind              TEXT NOT NULL,
    text              TEXT NOT NULL,
    novelty           TEXT NOT NULL,
    novelty_reasoning TEXT NOT NULL DEFAULT '',
    related_claim     TEXT,
    first_run_id      TEXT NOT NULL,
    first_seen_at     TEXT NOT NULL,
    last_seen_at      TEXT NOT NULL,
    PRIMARY KEY (ticker, fingerprint)
);
CREATE INDEX IF NOT EXISTS idx_claims_seen ON claims (ticker, first_seen_at);

-- Evidence. One row per (claim, video, moment); channel_id is what makes
-- "three different people said this" answerable after the fact.
CREATE TABLE IF NOT EXISTS claim_citations (
    ticker            TEXT    NOT NULL,
    fingerprint       TEXT    NOT NULL,
    video_id          TEXT    NOT NULL,
    timestamp_seconds INTEGER NOT NULL,
    quote_paraphrase  TEXT    NOT NULL,
    channel_id        TEXT    NOT NULL DEFAULT '',
    run_id            TEXT    NOT NULL,
    seen_at           TEXT    NOT NULL,
    PRIMARY KEY (ticker, fingerprint, video_id, timestamp_seconds)
);
CREATE INDEX IF NOT EXISTS idx_citations_claim
    ON claim_citations (ticker, fingerprint);

CREATE TABLE IF NOT EXISTS threads (
    thread_id       TEXT    PRIMARY KEY,
    run_id          TEXT    NOT NULL,
    ticker          TEXT    NOT NULL,
    generated_at    TEXT    NOT NULL,
    headline        TEXT    NOT NULL,
    new_claim_count INTEGER NOT NULL,
    payload_json    TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_threads_ticker ON threads (ticker, generated_at);
"""


def _resolve(db_path: Path | None) -> Path:
    return Path(db_path) if db_path is not None else DIGEST_DB_PATH


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def _is_v1(conn: sqlite3.Connection) -> bool:
    """True when ``claims`` still carries its citation columns inline."""
    return "video_id" in _columns(conn, "claims")


def _migrate_v1(conn: sqlite3.Connection) -> None:
    """Lift the inline citation columns out of ``claims`` into their own table.

    Ordering matters: the old table is renamed first so the fresh schema can
    create the new-shape ``claims`` alongside it.
    """
    log.info("Migrating digest database to schema v%d", SCHEMA_VERSION)
    conn.execute("ALTER TABLE claims RENAME TO claims_v1")
    conn.executescript(_SCHEMA)
    conn.execute(
        """
        INSERT OR IGNORE INTO claim_citations
            (ticker, fingerprint, video_id, timestamp_seconds, quote_paraphrase,
             channel_id, run_id, seen_at)
        SELECT ticker, fingerprint, video_id, timestamp_seconds, quote_paraphrase,
               ?, run_id, first_seen_at
        FROM claims_v1
        """,
        (UNKNOWN_CHANNEL,),
    )
    conn.execute(
        """
        INSERT OR IGNORE INTO claims
            (ticker, fingerprint, kind, text, novelty, novelty_reasoning,
             related_claim, first_run_id, first_seen_at, last_seen_at)
        SELECT ticker, fingerprint, kind, text, novelty, novelty_reasoning,
               related_claim, run_id, first_seen_at, first_seen_at
        FROM claims_v1
        """
    )
    conn.execute("DROP TABLE claims_v1")


def init_db(db_path: Path | None = None) -> Path:
    """Create or migrate the database, and return its path."""
    path = _resolve(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        if _is_v1(conn):
            _migrate_v1(conn)
        else:
            conn.executescript(_SCHEMA)
        conn.execute("DELETE FROM schema_version")
        conn.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
        conn.commit()
    return path


def _now() -> datetime:
    return datetime.now(timezone.utc)


def save_run(run: DigestRun, db_path: Path | None = None) -> None:
    """Persist a run, its claims, their citations and its thread."""
    path = init_db(db_path)
    source_label = run.channel.title if run.channel else run.request.ticker
    seen_at = run.generated_at.isoformat()

    # The run already knows which channel published each video, so citations
    # get their attribution here rather than asking the model for it.
    channel_by_video = {
        scored.metadata.video_id: scored.metadata.channel_id for scored in run.videos
    }

    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            INSERT INTO digest_runs
                (run_id, ticker, company_name, source_kind, source_label,
                 generated_at, video_count, payload_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET payload_json = excluded.payload_json
            """,
            (
                run.run_id,
                run.request.ticker,
                run.request.company_name,
                run.request.source_kind,
                source_label,
                seen_at,
                len(run.videos),
                run.model_dump_json(),
            ),
        )

        for claim in run.claims:
            first_seen = (claim.first_seen_at or run.generated_at).isoformat()
            conn.execute(
                """
                INSERT INTO claims
                    (ticker, fingerprint, kind, text, novelty, novelty_reasoning,
                     related_claim, first_run_id, first_seen_at, last_seen_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ticker, fingerprint) DO UPDATE SET
                    last_seen_at = excluded.last_seen_at,
                    novelty      = excluded.novelty
                """,
                (
                    claim.ticker,
                    claim.fingerprint,
                    claim.kind,
                    claim.text,
                    claim.novelty,
                    claim.novelty_reasoning,
                    claim.related_claim,
                    run.run_id,
                    first_seen,
                    seen_at,
                ),
            )
            for citation in claim.citations:
                conn.execute(
                    """
                    INSERT INTO claim_citations
                        (ticker, fingerprint, video_id, timestamp_seconds,
                         quote_paraphrase, channel_id, run_id, seen_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(ticker, fingerprint, video_id, timestamp_seconds)
                        DO NOTHING
                    """,
                    (
                        claim.ticker,
                        claim.fingerprint,
                        citation.video_id,
                        citation.timestamp_seconds,
                        citation.quote_paraphrase,
                        channel_by_video.get(citation.video_id, UNKNOWN_CHANNEL),
                        run.run_id,
                        seen_at,
                    ),
                )

        if run.thread is not None:
            thread = run.thread
            conn.execute(
                """
                INSERT INTO threads
                    (thread_id, run_id, ticker, generated_at, headline,
                     new_claim_count, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(thread_id) DO UPDATE SET
                    payload_json    = excluded.payload_json,
                    headline        = excluded.headline,
                    new_claim_count = excluded.new_claim_count
                """,
                (
                    thread.thread_id,
                    run.run_id,
                    thread.ticker,
                    thread.generated_at.isoformat(),
                    thread.headline,
                    thread.new_claim_count,
                    thread.model_dump_json(),
                ),
            )
        conn.commit()

    log.info(
        "Stored run %s for %s (%d claims, thread=%s)",
        run.run_id,
        run.request.ticker,
        len(run.claims),
        run.thread.thread_id if run.thread else "none",
    )


def known_claims(
    ticker: str,
    lookback_days: int = NOVELTY_LOOKBACK_DAYS,
    db_path: Path | None = None,
) -> list[Claim]:
    """Claims already stored for *ticker* within the lookback window.

    This is the corpus novelty is judged against — "is anything in these new
    videos actually new?" means "is it absent from this list?". Each claim
    comes back with every citation ever recorded for it.
    """
    path = init_db(db_path)
    cutoff = (_now() - timedelta(days=lookback_days)).isoformat()

    with sqlite3.connect(path) as conn:
        rows = conn.execute(
            """
            SELECT ticker, fingerprint, kind, text, novelty, novelty_reasoning,
                   related_claim, first_seen_at
            FROM claims
            WHERE ticker = ? AND first_seen_at >= ?
            ORDER BY first_seen_at DESC
            """,
            (ticker.upper(), cutoff),
        ).fetchall()
        citation_rows = conn.execute(
            """
            SELECT fingerprint, video_id, timestamp_seconds, quote_paraphrase
            FROM claim_citations
            WHERE ticker = ?
            ORDER BY timestamp_seconds
            """,
            (ticker.upper(),),
        ).fetchall()

    citations: dict[str, list[Citation]] = {}
    for fingerprint, video_id, timestamp, paraphrase in citation_rows:
        citations.setdefault(fingerprint, []).append(
            Citation(
                video_id=video_id,
                timestamp_seconds=timestamp,
                quote_paraphrase=paraphrase,
            )
        )

    return [
        Claim(
            ticker=row[0],
            fingerprint=row[1],
            kind=row[2],
            text=row[3],
            novelty=row[4],
            novelty_reasoning=row[5],
            related_claim=row[6],
            first_seen_at=datetime.fromisoformat(row[7]),
            citations=citations.get(row[1], []),
        )
        for row in rows
    ]


def known_claim_channels(
    ticker: str, db_path: Path | None = None
) -> dict[str, set[str]]:
    """Which channels have already made each claim, keyed by fingerprint.

    A fingerprint whose recorded channels include the unknown marker came from
    a pre-v2 database. The caller treats that as "can't tell" rather than
    guessing — see ``pipeline.mark_corroboration``.
    """
    path = init_db(db_path)
    with sqlite3.connect(path) as conn:
        rows = conn.execute(
            "SELECT fingerprint, channel_id FROM claim_citations WHERE ticker = ?",
            (ticker.upper(),),
        ).fetchall()

    channels: dict[str, set[str]] = {}
    for fingerprint, channel_id in rows:
        channels.setdefault(fingerprint, set()).add(channel_id)
    return channels


def list_threads(
    ticker: str | None = None,
    limit: int = 20,
    db_path: Path | None = None,
) -> list[InsightThread]:
    """Stored threads, newest first, optionally filtered to one ticker."""
    path = init_db(db_path)
    sql = "SELECT payload_json FROM threads"
    params: tuple = ()
    if ticker:
        sql += " WHERE ticker = ?"
        params = (ticker.upper(),)
    sql += " ORDER BY generated_at DESC LIMIT ?"
    params = params + (limit,)

    with sqlite3.connect(path) as conn:
        rows = conn.execute(sql, params).fetchall()
    return [InsightThread.model_validate_json(row[0]) for row in rows]


def get_thread(thread_id: str, db_path: Path | None = None) -> InsightThread | None:
    """One stored thread by id, or None."""
    path = init_db(db_path)
    with sqlite3.connect(path) as conn:
        row = conn.execute(
            "SELECT payload_json FROM threads WHERE thread_id = ?", (thread_id,)
        ).fetchone()
    if row is None:
        return None
    return InsightThread.model_validate_json(row[0])


def get_run(run_id: str, db_path: Path | None = None) -> DigestRun | None:
    """One stored run by id, or None."""
    path = init_db(db_path)
    with sqlite3.connect(path) as conn:
        row = conn.execute(
            "SELECT payload_json FROM digest_runs WHERE run_id = ?", (run_id,)
        ).fetchone()
    if row is None:
        return None
    return DigestRun.model_validate_json(row[0])
