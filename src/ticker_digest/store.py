"""SQLite storage for digest runs, tracked claims and generated threads.

This is what makes novelty detection possible: a claim is only "news" relative
to what we already stored, so every run writes its claims back with the date
they were first seen. Threads are stored whole — the thread *is* the
deliverable, and re-reading it should never require re-running the pipeline.

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

_SCHEMA = """
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

-- One row per distinct claim per ticker. first_seen_at is never overwritten:
-- that column is the whole point of the table.
CREATE TABLE IF NOT EXISTS claims (
    ticker            TEXT    NOT NULL,
    fingerprint       TEXT    NOT NULL,
    kind              TEXT    NOT NULL,
    text              TEXT    NOT NULL,
    video_id          TEXT    NOT NULL,
    timestamp_seconds INTEGER NOT NULL,
    quote_paraphrase  TEXT    NOT NULL,
    novelty           TEXT    NOT NULL,
    novelty_reasoning TEXT    NOT NULL DEFAULT '',
    related_claim     TEXT,
    run_id            TEXT    NOT NULL,
    first_seen_at     TEXT    NOT NULL,
    PRIMARY KEY (ticker, fingerprint)
);
CREATE INDEX IF NOT EXISTS idx_claims_seen ON claims (ticker, first_seen_at);

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


def init_db(db_path: Path | None = None) -> Path:
    """Create the database and its tables if they don't exist yet."""
    path = _resolve(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.executescript(_SCHEMA)
    return path


def _now() -> datetime:
    return datetime.now(timezone.utc)


def save_run(run: DigestRun, db_path: Path | None = None) -> None:
    """Persist a run, its claims and its thread in one transaction."""
    path = init_db(db_path)
    source_label = run.channel.title if run.channel else run.request.ticker

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
                run.generated_at.isoformat(),
                len(run.videos),
                run.model_dump_json(),
            ),
        )

        for claim in run.claims:
            conn.execute(
                """
                INSERT INTO claims
                    (ticker, fingerprint, kind, text, video_id, timestamp_seconds,
                     quote_paraphrase, novelty, novelty_reasoning, related_claim,
                     run_id, first_seen_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ticker, fingerprint) DO NOTHING
                """,
                (
                    claim.ticker,
                    claim.fingerprint,
                    claim.kind,
                    claim.text,
                    claim.citation.video_id,
                    claim.citation.timestamp_seconds,
                    claim.citation.quote_paraphrase,
                    claim.novelty,
                    claim.novelty_reasoning,
                    claim.related_claim,
                    run.run_id,
                    (claim.first_seen_at or run.generated_at).isoformat(),
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
    videos actually new?" means "is it absent from this list?".
    """
    path = init_db(db_path)
    cutoff = (_now() - timedelta(days=lookback_days)).isoformat()

    with sqlite3.connect(path) as conn:
        rows = conn.execute(
            """
            SELECT ticker, fingerprint, kind, text, video_id, timestamp_seconds,
                   quote_paraphrase, novelty, novelty_reasoning, related_claim,
                   first_seen_at
            FROM claims
            WHERE ticker = ? AND first_seen_at >= ?
            ORDER BY first_seen_at DESC
            """,
            (ticker.upper(), cutoff),
        ).fetchall()

    return [
        Claim(
            ticker=row[0],
            fingerprint=row[1],
            kind=row[2],
            text=row[3],
            citation=Citation(
                video_id=row[4],
                timestamp_seconds=row[5],
                quote_paraphrase=row[6],
            ),
            novelty=row[7],
            novelty_reasoning=row[8],
            related_claim=row[9],
            first_seen_at=datetime.fromisoformat(row[10]),
        )
        for row in rows
    ]


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
