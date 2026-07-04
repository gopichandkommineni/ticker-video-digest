"""One-time (idempotent) shrink of data/fintwit.db: drop stored raw_json.

The raw_tweets.raw_json column stored the full provider payload (capped at
50KB/tweet). It grew to ~half the file and pushed the git-tracked DB past
GitHub's 100MB per-file limit, which blocked every DB-writing workflow.

Nothing reads the stored column — cross-provider reconciliation uses the
in-memory Tweet.raw_json — so this NULLs it out and VACUUMs to reclaim the
space. Idempotent: once every row is already NULL the UPDATE matches nothing
and VACUUM is skipped, so it is safe to run on every backfill.

Usage:
  python scripts/shrink_fintwit_db.py [--db data/fintwit.db]
"""

import argparse
import os
import sys

from storage.db import _DEFAULT_DB, get_connection


def shrink(db_path: str | None = None) -> int:
    """NULL every non-null raw_json and VACUUM if anything changed.

    Returns the number of rows cleared (0 if already clean)."""
    conn = get_connection(db_path)
    try:
        with conn:
            cur = conn.execute(
                "UPDATE raw_tweets SET raw_json = NULL WHERE raw_json IS NOT NULL"
            )
            cleared = cur.rowcount
        if cleared:
            # VACUUM cannot run inside a transaction; the `with conn` block above
            # has already committed, so the connection is clean here.
            conn.execute("VACUUM")
        return cleared
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Drop stored raw_json from fintwit.db.")
    parser.add_argument("--db", default=None, help="path to fintwit.db (default: repo data/fintwit.db)")
    args = parser.parse_args()

    path = str(args.db) if args.db else str(_DEFAULT_DB)
    before = os.path.getsize(path) if os.path.exists(path) else None
    cleared = shrink(args.db)
    if cleared:
        print(f"shrink: cleared raw_json on {cleared} row(s) and VACUUMed")
    else:
        print("shrink: no rows with raw_json — nothing to do")

    if before is not None and os.path.exists(path):
        after = os.path.getsize(path)
        print(f"shrink: {before/1048576:.1f} MB -> {after/1048576:.1f} MB")


if __name__ == "__main__":
    sys.exit(main())
