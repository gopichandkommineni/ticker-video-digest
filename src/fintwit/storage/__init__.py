"""FinTwit SQLite storage layer."""

from .db import init_db, get_connection, close_connection
from .tweets import upsert_tweets
from .handles import normalize_handle, upsert_handle, update_handle_status, get_handle, list_handles
from .reads import get_tweets_by_handle, count_tweets
from .day_log import (
    populate_pending_days,
    get_pending_days,
    get_retryable_days,
    get_all_retryable_days,
    mark_day,
    day_summary,
    coverage_floor,
)

__all__ = [
    "init_db",
    "get_connection",
    "close_connection",
    "upsert_tweets",
    "normalize_handle",
    "upsert_handle",
    "update_handle_status",
    "get_handle",
    "list_handles",
    "get_tweets_by_handle",
    "count_tweets",
    "populate_pending_days",
    "get_pending_days",
    "get_retryable_days",
    "get_all_retryable_days",
    "mark_day",
    "day_summary",
    "coverage_floor",
]
