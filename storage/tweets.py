"""Tweet write path: upsert and handle-state update in one transaction."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .db import get_connection


@dataclass
class UpsertResult:
    inserted: int
    ignored: int


def upsert_tweets(
    tweets: list[dict[str, Any]],
    db_path: Path | str | None = None,
) -> UpsertResult:
    """
    Bulk-insert tweets (INSERT OR IGNORE) and update each affected handle's
    aggregate state in the same transaction.

    Returns counts of newly inserted vs already-present rows.

    Write-path rules enforced here:
    - Idempotent: re-inserting an existing tweet_id is a silent no-op.
    - After a successful write the handle row is updated: total_tweets,
      latest_tweet_utc, and tweets_watermark_utc are derived from the DB
      (not trusted from caller).
    - earliest_tweet_utc is set once on first backfill, never moved back.
    - Everything happens inside one transaction; if the write fails the
      handle row is left untouched.
    """
    if not tweets:
        return UpsertResult(inserted=0, ignored=0)

    conn = get_connection(db_path)
    try:
        with conn:
            inserted = 0
            for row in tweets:
                cur = conn.execute(
                    """
                    INSERT OR IGNORE INTO raw_tweets (
                        tweet_id, account_handle, display_name, user_id,
                        text, created_at_utc, type,
                        is_reply, is_quote, in_reply_to_id,
                        quoted_tweet_id, quoted_author_id, conversation_id,
                        like_count, retweet_count, reply_count, quote_count,
                        view_count, bookmark_count,
                        has_media, media_urls, url,
                        is_deleted, fetched_at, source_provider, raw_json
                    ) VALUES (
                        :tweet_id, :account_handle, :display_name, :user_id,
                        :text, :created_at_utc, :type,
                        :is_reply, :is_quote, :in_reply_to_id,
                        :quoted_tweet_id, :quoted_author_id, :conversation_id,
                        :like_count, :retweet_count, :reply_count, :quote_count,
                        :view_count, :bookmark_count,
                        :has_media, :media_urls, :url,
                        :is_deleted, :fetched_at, :source_provider, :raw_json
                    )
                    """,
                    _normalize(row),
                )
                inserted += cur.rowcount

            ignored = len(tweets) - inserted

            # Recompute handle state for each distinct handle in the batch.
            handles_in_batch: set[str] = {t["account_handle"] for t in tweets}
            for handle in handles_in_batch:
                _update_handle_aggregates(conn, handle)

        return UpsertResult(inserted=inserted, ignored=ignored)
    finally:
        conn.close()


def _update_handle_aggregates(conn: sqlite3.Connection, handle: str) -> None:
    """
    Derive and persist total_tweets, latest_tweet_utc, tweets_watermark_utc
    for *handle* from what is actually stored in raw_tweets.

    earliest_tweet_utc is set once (only if NULL) and never moved backward.
    """
    agg = conn.execute(
        """
        SELECT
            COUNT(*)                AS total,
            MAX(created_at_utc)     AS latest,
            MIN(created_at_utc)     AS earliest
        FROM raw_tweets
        WHERE account_handle = ?
        """,
        (handle,),
    ).fetchone()

    total = agg["total"] or 0
    latest = agg["latest"]
    earliest = agg["earliest"]

    # Upsert the handle row, preserving earliest_tweet_utc if already set.
    conn.execute(
        """
        INSERT INTO handles (handle, total_tweets, latest_tweet_utc,
                             tweets_watermark_utc, earliest_tweet_utc)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(handle) DO UPDATE SET
            total_tweets         = excluded.total_tweets,
            latest_tweet_utc     = excluded.latest_tweet_utc,
            tweets_watermark_utc = excluded.tweets_watermark_utc,
            earliest_tweet_utc   = COALESCE(handles.earliest_tweet_utc,
                                            excluded.earliest_tweet_utc)
        """,
        (handle, total, latest, latest, earliest),
    )


def _normalize(row: dict[str, Any]) -> dict[str, Any]:
    """Fill in missing keys with None so named-bind params don't raise."""
    keys = [
        "tweet_id", "account_handle", "display_name", "user_id",
        "text", "created_at_utc", "type",
        "is_reply", "is_quote", "in_reply_to_id",
        "quoted_tweet_id", "quoted_author_id", "conversation_id",
        "like_count", "retweet_count", "reply_count", "quote_count",
        "view_count", "bookmark_count",
        "has_media", "media_urls", "url",
        "is_deleted", "fetched_at", "source_provider", "raw_json",
    ]
    return {k: row.get(k) for k in keys}
