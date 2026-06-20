"""One-time migration: ingestion worker pool v1 (docs/ingestion-worker-pool-v1.md).

Applies the additive schema changes (via storage.db.init_db, which is
idempotent) and the §4.1 backfill rule to an existing fintwit.db:

  - day_fetch_log: tweet_count IS NOT NULL AND tweets_fetched IS NULL
        → tweets_fetched = tweet_count

`tweets_written` is deliberately left NULL on historical rows. We never
fetched the inserted-row count for those rows, so fabricating one (e.g. from
tweet_count) would assert a provenance we don't have — the same call made for
first_seen_at in ledger v1: honest absence beats a fabricated proxy.

Idempotent: a second run is a no-op (the WHERE clause excludes already-filled
rows). Supports --dry-run (prints what would change, writes nothing) and
--db PATH (default data/fintwit.db).

Usage:
  python scripts/migrate_worker_pool_v1.py [--db PATH] [--dry-run]
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

# Allow running as a plain script (python scripts/migrate_worker_pool_v1.py).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from storage.db import _DEFAULT_DB, get_connection, init_db  # noqa: E402


def _count(conn: sqlite3.Connection, sql: str) -> int:
    return conn.execute(sql).fetchone()[0]


def _has_column(conn: sqlite3.Connection, table: str, col: str) -> bool:
    return col in {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _rows_needing_backfill(conn: sqlite3.Connection) -> int:
    """Count 'ok-ish' rows whose tweets_fetched still needs seeding from tweet_count.

    On an un-migrated DB the tweets_fetched column may not exist yet; in that
    case every row with a non-NULL tweet_count would be backfilled.
    """
    if _has_column(conn, "day_fetch_log", "tweets_fetched"):
        return _count(
            conn,
            "SELECT COUNT(*) FROM day_fetch_log "
            "WHERE tweet_count IS NOT NULL AND tweets_fetched IS NULL",
        )
    return _count(
        conn,
        "SELECT COUNT(*) FROM day_fetch_log WHERE tweet_count IS NOT NULL",
    )


def migrate(db_path: Path, dry_run: bool) -> int:
    # Ensure the schema (incl. the two new columns) exists before we read/write.
    # On --dry-run we still need the column to report accurately, but we must not
    # write — so only call init_db on a real run. The dry-run path tolerates the
    # column being absent (see _rows_needing_backfill).
    if not dry_run:
        init_db(db_path)

    conn = get_connection(db_path)
    try:
        to_backfill = _rows_needing_backfill(conn)

        if dry_run:
            print("── DRY RUN — no writes ──")
            print(f"  would set tweets_fetched = tweet_count on {to_backfill} row(s)")
            print("  tweets_written left NULL on all historical rows (by design)")
            return 0

        with conn:
            conn.execute(
                "UPDATE day_fetch_log SET tweets_fetched = tweet_count "
                "WHERE tweet_count IS NOT NULL AND tweets_fetched IS NULL"
            )

        total = _count(conn, "SELECT COUNT(*) FROM day_fetch_log")
        fetched_non_null = _count(
            conn, "SELECT COUNT(*) FROM day_fetch_log WHERE tweets_fetched IS NOT NULL"
        )
        written_non_null = _count(
            conn, "SELECT COUNT(*) FROM day_fetch_log WHERE tweets_written IS NOT NULL"
        )

        print("── Ingestion worker pool v1 migration summary ──")
        print(f"  day_fetch_log rows:                 {total}")
        print(f"  tweets_fetched non-NULL (post):     {fetched_non_null}")
        print(f"  tweets_written non-NULL (post):     {written_non_null}")
        print(f"  rows backfilled this run:           {to_backfill}")
        return 0
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingestion worker pool v1 migration.")
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
