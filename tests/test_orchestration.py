"""
Orchestration layer tests — fake adapter only, no real API calls.

New architecture (v2 day-queue):
  - Both providers (getxapi + twitterapi) are called for every day.
  - Cross-provider count agreement replaces reached_floor as completeness oracle.
  - day_fetch_log table tracks per-day status; runner reads it for final outcome.
  - coverage_floor replaces watermark as the completeness signal.

Test inventory:
  T1.  New handle → backfill from Jan 1; all days ok → status=ready.
  T2.  Handle with prior ok days → delta (last 3 days); deduplication.
  T3.  One provider fails a day → that day is 'failed'; outcome=incomplete.
       Re-run heals it (failed day retried, both providers agree).
  T4.  Both providers return mismatched counts → day marked mismatch; incomplete.
       Re-run with agreement → ok.
  T5.  Stale handle (old status_since) → re-run; fresh → skipped.
  T6.  Double-run guard (fresh in-progress) → skipped, adapters not called.
  T7.  ingest_all isolation: one handle's adapter raises; batch continues.
  T8.  All days fail (both providers error) → outcome=incomplete, no coverage_floor.
"""

from __future__ import annotations

import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from fintwit.storage import init_db, get_handle, upsert_handle
from fintwit.storage.day_log import day_summary, mark_day, populate_pending_days
from fintwit.tweet_sources.base import Tweet, FetchResult, UserInfo

UTC = datetime.timezone.utc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _iso(dt: datetime.datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _tweet(id: str, created_at_utc: str) -> Tweet:
    return Tweet(
        id=id, created_at_utc=created_at_utc, text=f"tweet {id}",
        type="original", is_reply=False, is_quote=False,
        in_reply_to_id=None, quoted_tweet_id=None, quoted_author_id=None,
        conversation_id=None, like_count=0, retweet_count=0, reply_count=0,
        quote_count=0, view_count=None, bookmark_count=None,
        has_media=False, media_urls=[], url=None,
    )


class FakeSource:
    """
    Fake adapter for day-queue tests.

    tweets_by_day: {date_str: [Tweet, ...]} — what to return per day.
    fail_provider: if set to 'getxapi' or 'twitterapi', raises on that provider.
    """
    def __init__(
        self,
        tweets_by_day: dict[str, list[Tweet]] | None = None,
        fail_provider: str | None = None,
        provider_name: str = "fake",
    ):
        self.tweets_by_day = tweets_by_day or {}
        self.fail_provider = fail_provider
        self.provider_name = provider_name
        self.calls: list[tuple[str, datetime.date, datetime.date]] = []

    def fetch_user_info(self, handle: str) -> UserInfo:
        return UserInfo(handle=handle, display_name="Test", user_id="1",
                        created_at_utc=None, followers_count=0, following_count=0,
                        bio=None, is_verified=False, is_blue_verified=False)

    def fetch_tweets(self, handle: str, start: datetime.date, end: datetime.date) -> FetchResult:
        self.calls.append((handle, start, end))
        if self.fail_provider and self.provider_name == self.fail_provider:
            raise RuntimeError(f"Simulated {self.fail_provider} failure")
        tweets = self.tweets_by_day.get(start.isoformat(), [])
        return FetchResult(tweets=tweets, reached_floor=True)


def _make_get_source(gx_source: FakeSource, tw_source: FakeSource):
    """Return a get_source factory that yields the right fake per provider."""
    def _get_source(provider: str):
        if provider == "getxapi":
            return gx_source
        return tw_source
    return _get_source


@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    db = tmp_path / "test.db"
    init_db(db)
    return db


def _patch_sources(gx: FakeSource, tw: FakeSource):
    return patch("fintwit.orchestration.day_fetcher.get_source", side_effect=_make_get_source(gx, tw))


def _patch_delay():
    """Zero out INTER_DAY_DELAY so tests don't sleep."""
    return patch("fintwit.orchestration.day_fetcher.INTER_DAY_DELAY", 0.0)


# ---------------------------------------------------------------------------
# T1 — new handle backfill
# ---------------------------------------------------------------------------

def test_t1_new_handle_backfill(tmp_db: Path) -> None:
    """New handle → backfill; both providers agree → status=ready, coverage_floor set."""
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)

    tweets_today     = [_tweet("a", f"{today.isoformat()}T10:00:00Z")]
    tweets_yesterday = [_tweet("b", f"{yesterday.isoformat()}T10:00:00Z")]
    by_day = {today.isoformat(): tweets_today, yesterday.isoformat(): tweets_yesterday}

    gx = FakeSource(by_day, provider_name="getxapi")
    tw = FakeSource(by_day, provider_name="twitterapi")

    from fintwit.orchestration.runner import ingest_handle
    with _patch_sources(gx, tw), _patch_delay():
        # _backfill_since limits range to 2 days so the test is fast.
        result = ingest_handle("testuser", db_path=tmp_db, _backfill_since=yesterday, sequential=True)

    row = get_handle("testuser", db_path=tmp_db)
    print(f"\nT1: outcome={result.outcome}, floor={result.coverage_floor}, status={row['status']}")

    assert result.outcome == "ok", result
    assert row["status"] == "ready"
    assert result.coverage_floor is not None
    assert len(gx.calls) == 2   # one call per day (2 days)
    assert len(tw.calls) == 2


# ---------------------------------------------------------------------------
# T2 — delta run (handle with prior ok days)
# ---------------------------------------------------------------------------

def test_t2_delta_run_uses_last_3_days(tmp_db: Path) -> None:
    """Handle with prior ok days in day_fetch_log → delta uses last 3 days."""
    from fintwit.orchestration.runner import ingest_handle

    today = datetime.date.today()
    # Pre-populate some ok days so runner thinks backfill is done.
    since = today - datetime.timedelta(days=10)
    populate_pending_days("testuser", since, today - datetime.timedelta(days=4),
                          db_path=tmp_db)
    # Mark them all ok to simulate completed prior backfill.
    day = since
    while day <= today - datetime.timedelta(days=4):
        for prov in ("getxapi", "twitterapi"):
            mark_day("testuser", day.isoformat(), prov, status="ok",
                     tweet_count=5, db_path=tmp_db)
        day += datetime.timedelta(days=1)

    upsert_handle("testuser", {"status": "ready"}, db_path=tmp_db)

    gx = FakeSource(provider_name="getxapi")
    tw = FakeSource(provider_name="twitterapi")

    with _patch_sources(gx, tw), _patch_delay():
        result = ingest_handle("testuser", db_path=tmp_db, sequential=True)

    print(f"\nT2: outcome={result.outcome}, gx_calls={gx.calls}, tw_calls={tw.calls}")
    assert result.outcome == "ok"
    # Delta should only process the last 3 days (overlap window).
    dates_fetched = {start for (_, start, _) in gx.calls}
    min_fetched = min(dates_fetched) if dates_fetched else today
    assert (today - min_fetched).days <= 3, (
        f"delta should only fetch last 3 days, but fetched from {min_fetched}"
    )


# ---------------------------------------------------------------------------
# T3 — one provider fails → failed day → incomplete → retry heals
# ---------------------------------------------------------------------------

def test_t3_single_provider_failure_retried(tmp_db: Path) -> None:
    """One provider throws → day marked failed → outcome=incomplete.
    Second run with both providers ok → outcome=ok."""
    from fintwit.orchestration.runner import ingest_handle

    today = datetime.date.today()
    date_str = today.isoformat()
    tweets = [_tweet("x", f"{date_str}T10:00:00Z")]

    # First run: twitterapi fails.
    gx_ok = FakeSource({date_str: tweets}, provider_name="getxapi")
    tw_fail = FakeSource({date_str: tweets}, fail_provider="twitterapi", provider_name="twitterapi")

    with _patch_sources(gx_ok, tw_fail), _patch_delay():
        r1 = ingest_handle("testuser", db_path=tmp_db, _backfill_since=today, sequential=True)

    summary = day_summary("testuser", db_path=tmp_db)
    print(f"\nT3 run1: outcome={r1.outcome}, day_summary={summary}")
    assert r1.outcome == "incomplete"
    assert summary.get("failed", 0) > 0

    # Second run: both providers ok.
    gx_ok2 = FakeSource({date_str: tweets}, provider_name="getxapi")
    tw_ok2 = FakeSource({date_str: tweets}, provider_name="twitterapi")

    with _patch_sources(gx_ok2, tw_ok2), _patch_delay():
        r2 = ingest_handle("testuser", db_path=tmp_db, _backfill_since=today, sequential=True)

    print(f"T3 run2: outcome={r2.outcome}")
    assert r2.outcome == "ok"


# ---------------------------------------------------------------------------
# T4 — provider count mismatch → mismatch day → incomplete → retry heals
# ---------------------------------------------------------------------------

def test_t4_count_mismatch_marked_and_retried(tmp_db: Path) -> None:
    """Providers return very different counts → mismatch → incomplete.
    Second run with matching counts → ok."""
    from fintwit.orchestration.runner import ingest_handle

    today = datetime.date.today()
    date_str = today.isoformat()

    # GetXAPI returns 2 tweets, twitterapi returns 30 → >10% mismatch.
    few   = [_tweet(str(i), f"{date_str}T{i:02d}:00:00Z") for i in range(2)]
    many  = [_tweet(str(i), f"{date_str}T{i:02d}:00:00Z") for i in range(30)]
    gx_few  = FakeSource({date_str: few},  provider_name="getxapi")
    tw_many = FakeSource({date_str: many}, provider_name="twitterapi")

    with _patch_sources(gx_few, tw_many), _patch_delay():
        r1 = ingest_handle("testuser", db_path=tmp_db, _backfill_since=today, sequential=True)

    summary = day_summary("testuser", db_path=tmp_db)
    print(f"\nT4 run1: outcome={r1.outcome}, day_summary={summary}")
    assert r1.outcome == "incomplete"
    assert summary.get("mismatch", 0) > 0

    # Second run: both return same count → agreement → ok.
    same = [_tweet(str(i), f"{date_str}T{i:02d}:00:00Z") for i in range(15)]
    gx2 = FakeSource({date_str: same}, provider_name="getxapi")
    tw2 = FakeSource({date_str: same}, provider_name="twitterapi")

    with _patch_sources(gx2, tw2), _patch_delay():
        r2 = ingest_handle("testuser", db_path=tmp_db, _backfill_since=today, sequential=True)

    print(f"T4 run2: outcome={r2.outcome}")
    assert r2.outcome == "ok"


# ---------------------------------------------------------------------------
# T5 — stale handle retried; fresh handle skipped
# ---------------------------------------------------------------------------

def test_t5_stale_handle_is_retried(tmp_db: Path) -> None:
    from fintwit.orchestration.runner import is_stale, ingest_handle
    from fintwit.orchestration import config as cfg

    now = datetime.datetime.now(UTC)
    old_ts   = _iso(now - datetime.timedelta(minutes=cfg.STALE_THRESHOLD_MINUTES + 10))
    fresh_ts = _iso(now - datetime.timedelta(seconds=30))

    assert is_stale({"status": "backfilling", "status_since": old_ts})   is True
    assert is_stale({"status": "backfilling", "status_since": fresh_ts}) is False
    assert is_stale({"status": "fetching",    "status_since": old_ts})   is True
    assert is_stale({"status": "ready",       "status_since": old_ts})   is False

    today = datetime.date.today()
    date_str = today.isoformat()
    tweets = [_tweet("s", f"{date_str}T10:00:00Z")]
    gx = FakeSource({date_str: tweets}, provider_name="getxapi")
    tw = FakeSource({date_str: tweets}, provider_name="twitterapi")

    # Stale handle → should be re-run.
    upsert_handle("stuck", {"status": "backfilling", "status_since": old_ts}, db_path=tmp_db)
    with _patch_sources(gx, tw), _patch_delay():
        r_stale = ingest_handle("stuck", db_path=tmp_db, _backfill_since=today, sequential=True)

    row = get_handle("stuck", db_path=tmp_db)
    print(f"\nT5(stale): outcome={r_stale.outcome}, status={row['status']}")
    assert r_stale.outcome != "skipped"
    assert row["status"] not in ("backfilling", "fetching")

    # Fresh handle → should be skipped.
    upsert_handle("fresh", {"status": "backfilling", "status_since": fresh_ts}, db_path=tmp_db)
    gx2 = FakeSource(provider_name="getxapi")
    tw2 = FakeSource(provider_name="twitterapi")
    with _patch_sources(gx2, tw2), _patch_delay():
        r_fresh = ingest_handle("fresh", db_path=tmp_db, sequential=True)

    print(f"T5(fresh): outcome={r_fresh.outcome}, gx_calls={gx2.calls}")
    assert r_fresh.outcome == "skipped"
    assert len(gx2.calls) == 0


# ---------------------------------------------------------------------------
# T6 — double-run guard
# ---------------------------------------------------------------------------

def test_t6_double_run_skipped(tmp_db: Path) -> None:
    from fintwit.orchestration.runner import ingest_handle

    now = datetime.datetime.now(UTC)
    fresh_ts = _iso(now - datetime.timedelta(seconds=30))
    upsert_handle("testuser", {"status": "backfilling", "status_since": fresh_ts}, db_path=tmp_db)

    gx = FakeSource(provider_name="getxapi")
    tw = FakeSource(provider_name="twitterapi")
    with _patch_sources(gx, tw), _patch_delay():
        result = ingest_handle("testuser", db_path=tmp_db, sequential=True)

    assert result.outcome == "skipped"
    assert len(gx.calls) == 0
    print(f"\nT6: outcome={result.outcome}")


# ---------------------------------------------------------------------------
# T7 — ingest_all isolation
# ---------------------------------------------------------------------------

def test_t7_ingest_all_isolation(tmp_db: Path) -> None:
    from fintwit.orchestration.runner import ingest_all

    for h in ("alice", "bob", "carol"):
        upsert_handle(h, {"status": "pending"}, db_path=tmp_db)

    today = datetime.date.today()
    date_str = today.isoformat()
    tweets_ok = [_tweet("t", f"{date_str}T10:00:00Z")]

    def fake_get_source(provider: str):
        class FailForBob:
            def fetch_user_info(self, handle):
                return FakeSource().fetch_user_info(handle)
            def fetch_tweets(self, handle, start, end):
                if handle == "bob":
                    raise RuntimeError("broken")
                return FetchResult(tweets=tweets_ok, reached_floor=True)
        return FailForBob()

    with patch("fintwit.orchestration.day_fetcher.get_source", side_effect=fake_get_source), \
         _patch_delay():
        results = ingest_all(db_path=tmp_db, _backfill_since=today, sequential=True)

    by = {r.handle: r for r in results}
    print(f"\nT7: {[(r.handle, r.outcome) for r in results]}")
    assert by["alice"].outcome == "ok"
    assert by["bob"].outcome   in ("failed", "incomplete")
    assert by["carol"].outcome == "ok"
    assert get_handle("alice", db_path=tmp_db)["status"] == "ready"
    assert get_handle("carol", db_path=tmp_db)["status"] == "ready"


# ---------------------------------------------------------------------------
# T8 — all days fail → incomplete, no coverage_floor
# ---------------------------------------------------------------------------

def test_t8_all_days_failed_is_incomplete(tmp_db: Path) -> None:
    """Both providers fail every day → outcome=incomplete, coverage_floor=None."""
    from fintwit.orchestration.runner import ingest_handle

    gx_fail = FakeSource(fail_provider="getxapi",    provider_name="getxapi")
    tw_fail = FakeSource(fail_provider="twitterapi", provider_name="twitterapi")

    with _patch_sources(gx_fail, tw_fail), _patch_delay():
        result = ingest_handle("testuser", db_path=tmp_db, _backfill_since=datetime.date.today(), sequential=True)

    row = get_handle("testuser", db_path=tmp_db)
    print(f"\nT8: outcome={result.outcome}, floor={result.coverage_floor}, status={row['status']}")
    assert result.outcome == "incomplete"
    assert result.coverage_floor is None
    assert row["status"] == "incomplete"
