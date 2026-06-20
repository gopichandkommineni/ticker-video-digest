"""One-time migration: ingestion ledger v1 (docs/ingestion-ledger-gaps-v1.md).

Applies the additive schema changes (via storage.db.init_db, which is
idempotent) and the §4 backfill rules to an existing fintwit.db:

  - day_fetch_log: status='ok' AND last_succeeded_at IS NULL
        → last_succeeded_at = fetched_at
  - day_fetch_log: status='mismatch'
        → one mismatch_resolutions row per (handle, date) with
          resolution='unresolved', resolved_at=NULL.

Idempotent: a second run is a no-op. Supports --dry-run (prints what would
change, writes nothing) and --db PATH (default data/fintwit.db).

Usage:
  python scripts/migrate_ingestion_ledger_v1.py [--db PATH] [--dry-run]
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

# Allow running as a plain script (python scripts/migrate_ingestion_ledger_v1.py).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from storage.db import _DEFAULT_DB, get_connection, init_db  # noqa: E402


def _count(conn: sqlite3.Connection, table: str) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def _has_column(conn: sqlite3.Connection, table: str, col: str) -> bool:
    return col in {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _has_table(conn: sqlite3.Connection, table: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
    ).fetchone() is not None


def _ok_rows_needing_backfill(conn: sqlite3.Connection) -> int:
    # On an un-migrated DB the column does not exist yet; every 'ok' row with a
    # fetched_at would be backfilled.
    if _has_column(conn, "day_fetch_log", "last_succeeded_at"):
        return conn.execute(
            "SELECT COUNT(*) FROM day_fetch_log "
            "WHERE status = 'ok' AND last_succeeded_at IS NULL AND fetched_at IS NOT NULL"
        ).fetchone()[0]
    return conn.execute(
        "SELECT COUNT(*) FROM day_fetch_log "
        "WHERE status = 'ok' AND fetched_at IS NOT NULL"
    ).fetchone()[0]


def _mismatch_pairs(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    """Distinct (handle, date) pairs that ever had a status='mismatch' row."""
    rows = conn.execute(
        "SELECT DISTINCT handle, date FROM day_fetch_log "
        "WHERE status = 'mismatch' ORDER BY handle, date"
    ).fetchall()
    return [(r[0], r[1]) for r in rows]


def _mismatch_pairs_missing_resolution(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    # If the table doesn't exist yet (un-migrated DB), all pairs need seeding.
    if not _has_table(conn, "mismatch_resolutions"):
        return _mismatch_pairs(conn)
    return [
        (h, d)
        for (h, d) in _mismatch_pairs(conn)
        if conn.execute(
            "SELECT 1 FROM mismatch_resolutions WHERE handle = ? AND date = ?",
            (h, d),
        ).fetchone()
        is None
    ]


def _provider_counts(conn: sqlite3.Connection, handle: str, date: str) -> dict[str, int | None]:
    rows = conn.execute(
        "SELECT provider, tweet_count FROM day_fetch_log WHERE handle = ? AND date = ?",
        (handle, date),
    ).fetchall()
    return {r[0]: r[1] for r in rows}


def _seed_note(conn: sqlite3.Connection, handle: str, date: str) -> str | None:
    """Free-text seed note: pass the existing fetched_at through, or NULL."""
    row = conn.execute(
        "SELECT fetched_at FROM day_fetch_log WHERE handle = ? AND date = ? "
        "AND fetched_at IS NOT NULL LIMIT 1",
        (handle, date),
    ).fetchone()
    return row[0] if row else None


def migrate(db_path: Path, dry_run: bool) -> int:
    # Pre counts (open after init so the tables exist; pre/post compare the same DB).
    if not dry_run:
        init_db(db_path)

    conn = get_connection(db_path)
    try:
        pre_raw = _count(conn, "raw_tweets")
        pre_log = _count(conn, "day_fetch_log")
        pre_handles = _count(conn, "handles")

        ok_to_backfill = _ok_rows_needing_backfill(conn)
        pairs_to_seed = _mismatch_pairs_missing_resolution(conn)

        if dry_run:
            print("── DRY RUN — no writes ──")
            print(f"  would set last_succeeded_at on {ok_to_backfill} 'ok' day_fetch_log row(s)")
            print(f"  would insert {len(pairs_to_seed)} mismatch_resolutions row(s):")
            for h, d in pairs_to_seed:
                print(f"      ({h}, {d})")
            # mismatch_resolutions may not exist yet if init was never run.
            try:
                mr = _count(conn, "mismatch_resolutions")
            except sqlite3.OperationalError:
                mr = 0
            print(f"  mismatch_resolutions current rows: {mr}")
            return 0

        # --- Backfill 1: last_succeeded_at = fetched_at for 'ok' rows. ---
        with conn:
            conn.execute(
                "UPDATE day_fetch_log SET last_succeeded_at = fetched_at "
                "WHERE status = 'ok' AND last_succeeded_at IS NULL "
                "AND fetched_at IS NOT NULL"
            )

        # --- Backfill 2: seed mismatch_resolutions (one per handle/date). ---
        with conn:
            for handle, date in pairs_to_seed:
                counts = _provider_counts(conn, handle, date)
                conn.execute(
                    """
                    INSERT OR IGNORE INTO mismatch_resolutions (
                        handle, date, getxapi_count, twitterapi_count,
                        resolution, note, resolved_at
                    ) VALUES (?, ?, ?, ?, 'unresolved', ?, NULL)
                    """,
                    (
                        handle,
                        date,
                        counts.get("getxapi"),
                        counts.get("twitterapi"),
                        _seed_note(conn, handle, date),
                    ),
                )

        # Post counts.
        post_raw = _count(conn, "raw_tweets")
        post_log = _count(conn, "day_fetch_log")
        post_handles = _count(conn, "handles")
        last_succeeded = conn.execute(
            "SELECT COUNT(*) FROM day_fetch_log WHERE last_succeeded_at IS NOT NULL"
        ).fetchone()[0]
        mr_count = _count(conn, "mismatch_resolutions")

        print("── Ingestion ledger v1 migration summary ──")
        print(f"  raw_tweets     rows: {pre_raw} pre / {post_raw} post")
        print(f"  day_fetch_log  rows: {pre_log} pre / {post_log} post")
        print(f"  handles        rows: {pre_handles} pre / {post_handles} post")
        print(f"  day_fetch_log.last_succeeded_at non-NULL: {last_succeeded}")
        print(f"  mismatch_resolutions rows: {mr_count}")
        return 0
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingestion ledger v1 migration.")
    parser.add_argument(
        "--db", default=str(_DEFAULT_DB),
        help="Path to fintwit.db (default: data/fintwit.db)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print what would change without writing.",
    )
    args = parser.parse_args()
    return migrate(Path(args.db), dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
