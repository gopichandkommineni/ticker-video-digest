"""Day-queue fetcher: the single unified loop for backfill and daily runs.

Architecture
============
- Splits any date window into per-day slices.
- Fetches each day from both providers independently.
- Verifies completeness by cross-provider count agreement.
- Persists progress in day_fetch_log (idempotent — skips ok days on re-run).
- Rate-limiting: a configurable inter-day sleep (default 1 s) keeps requests
  well within API limits without any external queue or service.
- reached_floor is never read. Completeness is determined entirely by
  cross-provider count agreement and the day_fetch_log status column.

Status flow per (handle, date, provider):
  pending → ok       both providers agree within MISMATCH_THRESHOLD
  pending → mismatch providers disagree; retried on the next daily sweep
  pending → failed   provider raised an exception; retried up to MAX_RETRIES
"""

from __future__ import annotations

import datetime
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from fintwit.tweet_sources.factory import get_source
from fintwit.storage.db import get_connection
from fintwit.storage.day_log import (
    mark_day,
    populate_pending_days,
    get_pending_days,
    get_retryable_days,
)
from fintwit.storage.tweets import upsert_tweets

logger = logging.getLogger(__name__)

_UTC = datetime.timezone.utc

PROVIDERS: tuple[str, ...] = ("getxapi", "twitterapi")

# Count-agreement threshold: days where the two providers differ by more than
# this fraction of the larger count are marked mismatch and retried.
MISMATCH_THRESHOLD: float = 0.10

# Days marked mismatch or failed are retried this many times before being
# left as-is (still in DB as mismatch/failed for manual review).
MAX_RETRIES: int = 3

# Sleep between consecutive day-level requests (not page-level) to avoid
# triggering anti-abuse rate limits. Configurable via env if needed.
INTER_DAY_DELAY: float = 1.0


def _iso_now() -> str:
    return datetime.datetime.now(tz=_UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _to_storage_rows(
    tweets: list,
    handle: str,
    provider: str,
) -> list[dict]:
    fetched_at = _iso_now()
    return [
        {
            "tweet_id":        t.id,
            "account_handle":  handle,
            "display_name":    None,
            "user_id":         None,
            "text":            t.text,
            "created_at_utc":  t.created_at_utc,
            "type":            t.type,
            "is_reply":        int(t.is_reply),
            "is_quote":        int(t.is_quote),
            "in_reply_to_id":  t.in_reply_to_id,
            "quoted_tweet_id": t.quoted_tweet_id,
            "quoted_author_id":t.quoted_author_id,
            "conversation_id": t.conversation_id,
            "like_count":      t.like_count,
            "retweet_count":   t.retweet_count,
            "reply_count":     t.reply_count,
            "quote_count":     t.quote_count,
            "view_count":      t.view_count,
            "bookmark_count":  t.bookmark_count,
            "has_media":       int(t.has_media),
            "media_urls":      ",".join(t.media_urls) if t.media_urls else None,
            "url":             t.url,
            "is_deleted":      0,
            "fetched_at":      fetched_at,
            "source_provider": provider,
            # raw_json is intentionally NOT persisted: the full provider payload
            # (capped at 50KB/tweet) was ~half of data/fintwit.db and pushed the
            # git-tracked file past GitHub's 100MB limit. Nothing reads the
            # stored column — cross-provider reconciliation uses the in-memory
            # Tweet.raw_json instead — so dropping it is lossless for the
            # pipeline. See scripts/shrink_fintwit_db.py for the one-time
            # backfill of existing rows.
            "raw_json":        None,
        }
        for t in tweets
    ]


@dataclass
class DayFetchSummary:
    handle: str
    ok: int = 0
    mismatch: int = 0
    failed: int = 0
    skipped_ok: int = 0
    tweets_inserted: int = 0
    tweets_ignored: int = 0
    days_processed: list[str] = field(default_factory=list)
    mismatch_days: list[str] = field(default_factory=list)
    failed_days: list[str] = field(default_factory=list)


def _fetch_one_day(
    handle: str,
    date_str: str,
    provider: str,
    db_path: Path | str | None,
    inter_day_delay: float,
) -> tuple[int, str | None]:
    """
    Fetch one (handle, date, provider) combination.
    Returns (tweet_count, error_message_or_None).
    Writes tweets to raw_tweets. Updates day_fetch_log to failed on exception.
    Caller is responsible for the final ok/mismatch mark after both providers run.
    """
    day = datetime.date.fromisoformat(date_str)
    src = get_source(provider)
    try:
        result = src.fetch_tweets(handle, day, day)
    except Exception as exc:
        logger.warning("[%s] %s %s — fetch error: %s", provider, handle, date_str, exc)
        mark_day(
            handle, date_str, provider,
            status="failed", tweet_count=0, error=str(exc),
            increment_retry=True, db_path=db_path,
        )
        return 0, str(exc)

    if result.tweets:
        rows = _to_storage_rows(result.tweets, handle, provider)
        try:
            upsert_result = upsert_tweets(rows, db_path=db_path)
            logger.debug(
                "[%s] %s %s — %d tweets (inserted=%d ignored=%d)",
                provider, handle, date_str,
                len(result.tweets), upsert_result.inserted, upsert_result.ignored,
            )
        except Exception as exc:
            logger.warning("[%s] %s %s — upsert error: %s", provider, handle, date_str, exc)
            mark_day(
                handle, date_str, provider,
                status="failed", tweet_count=len(result.tweets), error=str(exc),
                increment_retry=True, db_path=db_path,
            )
            return len(result.tweets), str(exc)

    time.sleep(inter_day_delay)
    return len(result.tweets), None


def _verify_and_mark(
    handle: str,
    date_str: str,
    counts: dict[str, int | None],
    errors: dict[str, str | None],
    db_path: Path | str | None,
) -> str:
    """
    Cross-verify the two provider counts for one day.
    Returns the final day status: 'ok' | 'mismatch' | 'failed'.
    Marks both providers in day_fetch_log.
    reached_floor is NOT consulted — count agreement is the sole oracle.
    """
    gx_err = errors.get("getxapi")
    tw_err = errors.get("twitterapi")

    if gx_err and tw_err:
        # Both failed — mark both; will retry via retryable sweep.
        for provider in PROVIDERS:
            mark_day(handle, date_str, provider, status="failed",
                     tweet_count=counts.get(provider, 0),
                     increment_retry=False, db_path=db_path)
        return "failed"

    gx_count = counts.get("getxapi", 0) or 0
    tw_count = counts.get("twitterapi", 0) or 0
    max_count = max(gx_count, tw_count, 1)
    diff_frac = abs(gx_count - tw_count) / max_count

    if diff_frac <= MISMATCH_THRESHOLD:
        status = "ok"
    else:
        status = "mismatch"
        logger.warning(
            "%s %s — mismatch: getxapi=%d twitterapi=%d (%.0f%% diff)",
            handle, date_str, gx_count, tw_count, diff_frac * 100,
        )

    for provider in PROVIDERS:
        if errors.get(provider):
            # One provider failed; other may be ok — mark each independently.
            # The failed one was already marked by _fetch_one_day.
            pass
        else:
            mark_day(
                handle, date_str, provider,
                status=status,
                tweet_count=counts.get(provider, 0),
                increment_retry=(status == "mismatch"),
                db_path=db_path,
            )

    return status


def run_days(
    handle: str,
    days: list[dict],
    db_path: Path | str | None = None,
    inter_day_delay: float = INTER_DAY_DELAY,
) -> DayFetchSummary:
    """
    Process a list of day rows (from day_fetch_log).
    Fetches each day from both providers, unions into raw_tweets, verifies.
    Returns a DayFetchSummary with per-status counts.
    """
    summary = DayFetchSummary(handle=handle)

    # Group rows by date so we process both providers per date before moving on.
    dates: dict[str, set[str]] = {}
    for row in days:
        dates.setdefault(row["date"], set()).add(row["provider"])

    for date_str in sorted(dates):
        providers_needed = dates[date_str]
        counts: dict[str, int | None] = {}
        errors: dict[str, str | None] = {}

        for provider in PROVIDERS:
            if provider not in providers_needed:
                continue
            count, err = _fetch_one_day(handle, date_str, provider, db_path, inter_day_delay)
            counts[provider] = count
            errors[provider] = err

        day_status = _verify_and_mark(handle, date_str, counts, errors, db_path)
        summary.days_processed.append(date_str)

        if day_status == "ok":
            summary.ok += 1
        elif day_status == "mismatch":
            summary.mismatch += 1
            summary.mismatch_days.append(date_str)
        else:
            summary.failed += 1
            summary.failed_days.append(date_str)

    return summary


def backfill_handle(
    handle: str,
    since: datetime.date,
    until: datetime.date,
    db_path: Path | str | None = None,
    inter_day_delay: float = INTER_DAY_DELAY,
    max_retries: int = MAX_RETRIES,
) -> DayFetchSummary:
    """
    Full backfill for one handle over [since, until].

    1. Populate pending rows for all days not yet in day_fetch_log.
    2. Fetch all pending days (both providers, cross-verify).
    3. One retry pass over any mismatch/failed days from this run.

    Idempotent: re-running skips ok days and only processes what's still pending
    or retryable. Progress is committed to day_fetch_log after each day so a
    job timeout does not lose work.
    """
    new_rows = populate_pending_days(handle, since, until, PROVIDERS, db_path)
    logger.info("backfill %s: %d new day-slots populated (%s → %s)", handle, new_rows, since, until)

    pending = get_pending_days(handle, PROVIDERS, db_path)
    logger.info("backfill %s: %d pending day-slots to fetch", handle, len(pending))

    summary = run_days(handle, pending, db_path, inter_day_delay)

    # One immediate retry pass over anything that failed in this run.
    retryable = get_retryable_days(handle, max_retries, PROVIDERS, db_path)
    if retryable:
        logger.info("backfill %s: retrying %d mismatch/failed day-slots", handle, len(retryable))
        retry_summary = run_days(handle, retryable, db_path, inter_day_delay)
        summary.ok += retry_summary.ok
        summary.mismatch = retry_summary.mismatch
        summary.failed = retry_summary.failed
        summary.mismatch_days = retry_summary.mismatch_days
        summary.failed_days = retry_summary.failed_days

    return summary


def delta_handle(
    handle: str,
    overlap_days: int = 3,
    db_path: Path | str | None = None,
    inter_day_delay: float = INTER_DAY_DELAY,
    max_retries: int = MAX_RETRIES,
) -> DayFetchSummary:
    """
    Daily delta for one handle.

    Fetches the last `overlap_days` days (default 3: catches late-propagating tweets)
    plus retries any outstanding mismatch/failed days from prior runs.
    Uses the same day-queue path as backfill — no separate code path, no watermark.
    """
    today = datetime.date.today()
    since = today - datetime.timedelta(days=overlap_days - 1)

    new_rows = populate_pending_days(handle, since, today, PROVIDERS, db_path)
    logger.info("delta %s: %d new day-slots (%s → %s)", handle, new_rows, since, today)

    pending = get_pending_days(handle, PROVIDERS, db_path)
    summary = run_days(handle, pending, db_path, inter_day_delay)

    # Sweep outstanding retryable days from any prior run.
    retryable = get_retryable_days(handle, max_retries, PROVIDERS, db_path)
    if retryable:
        logger.info("delta %s: retrying %d outstanding mismatch/failed day-slots", handle, len(retryable))
        retry_summary = run_days(handle, retryable, db_path, inter_day_delay)
        summary.ok += retry_summary.ok
        summary.mismatch += retry_summary.mismatch
        summary.failed += retry_summary.failed
        summary.mismatch_days += retry_summary.mismatch_days
        summary.failed_days += retry_summary.failed_days

    return summary
