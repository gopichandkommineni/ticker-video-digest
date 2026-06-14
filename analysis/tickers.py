"""Deterministic cashtag (ticker) extraction from stored tweets.

Pass 1 of the analysis pipeline: pure regex, no API calls. Populates the
ticker_mentions table (one row per distinct (tweet_id, ticker)), which is the
substrate the later Claude sentiment pass joins onto per (tweet, ticker).

Mention semantics: tweet-level and distinct — a tweet that says "$RKLB $RKLB"
counts once for RKLB. A tweet mentioning $RKLB and $ASTS yields two rows.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import yaml

from storage.db import get_connection, init_db

logger = logging.getLogger(__name__)

_THEMES = Path(__file__).parent.parent / "config" / "themes.yaml"

# $ + 1-5 uppercase letters, not followed by another letter/digit so we don't
# clip "$ABCDEF" into "$ABCDE". Lowercase cashtags are not valid tickers.
_CASHTAG_RE = re.compile(r"\$([A-Z]{1,5})(?![A-Za-z0-9])")


def extract_cashtags(text: str | None) -> set[str]:
    """Return the distinct set of cashtag symbols in *text* (without the $)."""
    if not text:
        return set()
    return set(_CASHTAG_RE.findall(text))


def load_universe(themes_path: Path | str | None = None) -> set[str]:
    """Return the canonical ticker universe from config/themes.yaml (read-only)."""
    path = Path(themes_path) if themes_path else _THEMES
    data = yaml.safe_load(path.read_text())
    universe: set[str] = set()
    for sector in data.get("sectors", {}).values():
        universe.update(sector.get("tickers", []))
    return universe


def rebuild_mentions(db_path: Path | str | None = None) -> int:
    """
    (Re)populate ticker_mentions from raw_tweets. Idempotent: clears the table
    and rebuilds, so it always reflects the current corpus and universe.
    Returns the number of mention rows written.
    """
    init_db(db_path)
    universe = load_universe()
    conn = get_connection(db_path)
    try:
        with conn:
            conn.execute("DELETE FROM ticker_mentions")
            rows = conn.execute(
                "SELECT tweet_id, account_handle, text, created_at_utc FROM raw_tweets"
            ).fetchall()
            written = 0
            for r in rows:
                for ticker in extract_cashtags(r["text"]):
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO ticker_mentions
                            (tweet_id, account_handle, ticker, in_universe, created_at_utc)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            r["tweet_id"],
                            r["account_handle"],
                            ticker,
                            1 if ticker in universe else 0,
                            r["created_at_utc"],
                        ),
                    )
                    written += 1
    finally:
        conn.close()
    logger.info("rebuild_mentions: wrote %d mention rows from %d tweets", written, len(rows))
    return written
