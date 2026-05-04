"""One-time cleanup: delete corrupted news_items rows.

Run manually after the news parser hotfix is deployed:

    uv run python scripts/cleanup_corrupt_news.py

Corrupted rows have empty titles or epoch-zero timestamps caused by yfinance
changing its news response format in 2025. The fixed parser skips bad items,
so this script only needs to be run once to clear the existing bad data.
"""

import sqlite3
from pathlib import Path

DB = Path("data/snapshots.db")


def main() -> None:
    if not DB.exists():
        print(f"Database not found at {DB} — nothing to clean.")
        return

    with sqlite3.connect(DB) as conn:
        cursor = conn.execute(
            """
            DELETE FROM news_items
            WHERE title IS NULL
               OR title = ''
               OR published_at = '1970-01-01T00:00:00+00:00'
               OR published_at LIKE '1970-%'
            """
        )
        print(f"Deleted {cursor.rowcount} corrupted news_items rows.")


if __name__ == "__main__":
    main()
