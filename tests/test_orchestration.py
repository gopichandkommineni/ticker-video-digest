"""
Orchestration layer tests — fake adapter only, no real API calls.

T1. New handle -> backfill range starts Jan 1 current year (computed at runtime);
    status pending->backfilling->ready; watermark = max created_at of written tweets.
T2. Second run on ready handle -> delta range = watermark-1h -> now; overlap deduped.
T3. PARTIAL FETCH (adapter raises): watermark UNCHANGED; status=failed; partial tweets
    retained. Retry completes cleanly; watermark advances — gap self-heals.  KEY TEST.
T4. WRITE FAILURE (upsert raises): watermark UNCHANGED; status=failed.  KEY TEST.
T5. STALE: handle in backfilling with old status_since -> is_stale() True;
    fresh status_since -> False; runner actually writes status_since on each
    in-progress transition.
T6. DOUBLE-RUN: freshly-backfilling handle (not stale) -> skipped, adapter not called.
T7. ingest_all ISOLATION: one handle's adapter raises; batch continues; only that
    handle ends failed.
"""

from __future__ import annotations

import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from storage import init_db, get_handle, upsert_handle
from storage.db import get_connection
from tweet_sources.base import Tweet, UserInfo

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
    Fake adapter. pages: successive fetch_tweets calls pop from this list.
    fail_on_call: 0-based index on which to raise RuntimeError.
    """
    def __init__(self, pages=None, fail_on_call=None):
        self.pages = list(pages or [[]])
        self.fail_on_call = fail_on_call
        self._call_count = 0
        self.last_start = None
        self.last_end = None

    def fetch_user_info(self, handle: str) -> UserInfo:
        return UserInfo(handle=handle, display_name="Test", user_id="1",
                        created_at_utc=None, followers_count=0, following_count=0,
                        bio=None, is_verified=False, is_blue_verified=False)

    def fetch_tweets(self, handle: str, start: datetime.date, end: datetime.date):
        self.last_start = start
        self.last_end = end
        idx = self._call_count
        self._call_count += 1
        if self.fail_on_call is not None and idx == self.fail_on_call:
            raise RuntimeError(f"Simulated failure on call {idx}")
        return self.pages[idx] if idx < len(self.pages) else []


@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    db = tmp_path / "test.db"
    init_db(db)
    return db


def _patch(fake: FakeSource):
    return patch("orchestration.runner.get_source", return_value=fake)


# ---------------------------------------------------------------------------
# T1
# ---------------------------------------------------------------------------

def test_t1_new_handle_backfill(tmp_db: Path) -> None:
    now = datetime.datetime.now(UTC)

    tweets = [
        _tweet("1", "2026-03-01T10:00:00Z"),
        _tweet("2", "2026-04-15T12:00:00Z"),
        _tweet("3", "2026-05-20T08:00:00Z"),
    ]
    fake = FakeSource(pages=[tweets])
    with _patch(fake):
        from orchestration.runner import ingest_handle
        result = ingest_handle("testuser", provider="fake", db_path=tmp_db)

    assert result.outcome == "ok", result
    assert result.watermark == "2026-05-20T08:00:00Z"
    assert result.inserted == 3
    assert result.ignored == 0

    row = get_handle("testuser", db_path=tmp_db)
    assert row["status"] == "ready"
    assert row["tweets_watermark_utc"] == "2026-05-20T08:00:00Z"
    assert row["total_tweets"] == 3
    assert fake.last_start == datetime.date(now.year, 1, 1)
    print(f"\nT1: backfill start={fake.last_start}, watermark={result.watermark}")


# ---------------------------------------------------------------------------
# T2
# ---------------------------------------------------------------------------

def test_t2_delta_run_deduplication(tmp_db: Path) -> None:
    from orchestration.runner import ingest_handle

    with _patch(FakeSource(pages=[[_tweet("1", "2026-03-01T10:00:00Z"),
                                    _tweet("2", "2026-05-20T08:00:00Z")]])):
        r1 = ingest_handle("testuser", provider="fake", db_path=tmp_db)
    assert r1.watermark == "2026-05-20T08:00:00Z"

    fake2 = FakeSource(pages=[[_tweet("2", "2026-05-20T08:00:00Z"),
                                _tweet("3", "2026-05-21T09:00:00Z")]])
    with _patch(fake2):
        r2 = ingest_handle("testuser", provider="fake", db_path=tmp_db)

    assert r2.outcome == "ok"
    assert r2.inserted == 1
    assert r2.ignored == 1
    assert get_handle("testuser", db_path=tmp_db)["total_tweets"] == 3

    wm = datetime.datetime(2026, 5, 20, 8, 0, 0, tzinfo=UTC)
    assert fake2.last_start == (wm - datetime.timedelta(hours=1)).date()
    print(f"\nT2: delta start={fake2.last_start}, total_tweets=3")


# ---------------------------------------------------------------------------
# T3
# ---------------------------------------------------------------------------

def test_t3_partial_fetch_watermark_unchanged(tmp_db: Path) -> None:
    from orchestration.runner import ingest_handle

    with _patch(FakeSource(pages=[[_tweet("1", "2026-03-01T10:00:00Z")]])):
        r0 = ingest_handle("testuser", provider="fake", db_path=tmp_db)
    wm_before = r0.watermark
    print(f"\nT3: watermark before partial-fetch run: {wm_before}")

    with _patch(FakeSource(fail_on_call=0)):
        r_fail = ingest_handle("testuser", provider="fake", db_path=tmp_db)

    row_fail = get_handle("testuser", db_path=tmp_db)
    wm_after_fail = row_fail["tweets_watermark_utc"]
    print(f"T3: watermark after partial-fetch run: {wm_after_fail}, status={row_fail['status']}")
    assert r_fail.outcome == "failed"
    assert wm_after_fail == wm_before, f"before={wm_before} after={wm_after_fail}"
    assert row_fail["status"] == "failed"

    conn = get_connection(tmp_db)
    count = conn.execute("SELECT COUNT(*) FROM raw_tweets WHERE account_handle='testuser'").fetchone()[0]
    conn.close()
    assert count == 1

    retry_tweets = [_tweet("1", "2026-03-01T10:00:00Z"), _tweet("2", "2026-05-21T09:00:00Z")]
    with _patch(FakeSource(pages=[retry_tweets])):
        r_retry = ingest_handle("testuser", provider="fake", db_path=tmp_db)

    wm_retry = get_handle("testuser", db_path=tmp_db)["tweets_watermark_utc"]
    print(f"T3: watermark after retry: {wm_retry}")
    assert r_retry.outcome == "ok"
    assert wm_retry == "2026-05-21T09:00:00Z"


# ---------------------------------------------------------------------------
# T4
# ---------------------------------------------------------------------------

def test_t4_write_failure_watermark_unchanged(tmp_db: Path) -> None:
    from orchestration.runner import ingest_handle

    with _patch(FakeSource(pages=[[_tweet("1", "2026-03-01T10:00:00Z")]])):
        r0 = ingest_handle("testuser", provider="fake", db_path=tmp_db)
    wm_before = r0.watermark
    print(f"\nT4: watermark before write-fail run: {wm_before}")

    with _patch(FakeSource(pages=[[_tweet("2", "2026-05-21T09:00:00Z")]])), \
         patch("orchestration.runner.upsert_tweets", side_effect=RuntimeError("disk full")):
        r_fail = ingest_handle("testuser", provider="fake", db_path=tmp_db)

    row = get_handle("testuser", db_path=tmp_db)
    wm_after = row["tweets_watermark_utc"]
    print(f"T4: watermark after write-fail run: {wm_after}, status={row['status']}")
    assert r_fail.outcome == "failed"
    assert wm_after == wm_before, f"before={wm_before} after={wm_after}"
    assert row["status"] == "failed"


# ---------------------------------------------------------------------------
# T5 — stale handle is actually retried, not skipped
# ---------------------------------------------------------------------------

def test_t5_stale_handle_is_retried(tmp_db: Path) -> None:
    """
    A handle stuck in backfilling with status_since > STALE_THRESHOLD_MINUTES:
      (a) is_stale() returns True
      (b) ingest_handle RE-RUNS it (outcome != skipped, adapter is called)
      (c) status transitions out of backfilling (to ready or failed)

    A handle freshly in backfilling (status_since = now):
      (d) is_stale() returns False
      (e) ingest_handle SKIPS it (outcome == skipped, adapter not called)
    """
    from orchestration.runner import is_stale, ingest_handle
    from orchestration import config as cfg

    now = datetime.datetime.now(UTC)
    old_ts   = _iso(now - datetime.timedelta(minutes=cfg.STALE_THRESHOLD_MINUTES + 10))
    fresh_ts = _iso(now - datetime.timedelta(seconds=30))

    # (a) is_stale() correctness
    assert is_stale({"status": "backfilling", "status_since": old_ts})   is True,  "old handle should be stale"
    assert is_stale({"status": "backfilling", "status_since": fresh_ts}) is False, "fresh handle should not be stale"
    assert is_stale({"status": "fetching",    "status_since": old_ts})   is True,  "fetching also stale when old"
    assert is_stale({"status": "ready",       "status_since": old_ts})   is False, "ready is never stale"

    # (b/c) Stale handle → ingest_handle re-runs it.
    # Set up handle stuck in backfilling with an old status_since.
    upsert_handle("stuck", {"status": "backfilling", "status_since": old_ts}, db_path=tmp_db)
    tweets = [_tweet("x1", "2026-05-01T10:00:00Z")]
    fake_stale = FakeSource(pages=[tweets])
    with _patch(fake_stale):
        r_stale = ingest_handle("stuck", provider="fake", db_path=tmp_db)

    row_stale = get_handle("stuck", db_path=tmp_db)
    print(f"\nT5(stale): outcome={r_stale.outcome}, adapter_calls={fake_stale._call_count}, status={row_stale['status']}")
    assert r_stale.outcome != "skipped",      "stale handle must be re-run, not skipped"
    assert fake_stale._call_count == 1,       "adapter must be called for stale handle"
    assert row_stale["status"] != "backfilling", "status must have advanced out of backfilling"

    # (d/e) Fresh handle → ingest_handle skips it.
    upsert_handle("fresh", {"status": "backfilling", "status_since": fresh_ts}, db_path=tmp_db)
    fake_fresh = FakeSource(pages=[[]])
    with _patch(fake_fresh):
        r_fresh = ingest_handle("fresh", provider="fake", db_path=tmp_db)

    print(f"T5(fresh): outcome={r_fresh.outcome}, adapter_calls={fake_fresh._call_count}")
    assert r_fresh.outcome == "skipped", "fresh in-progress handle must be skipped"
    assert fake_fresh._call_count == 0,  "adapter must NOT be called for fresh handle"

    # Runner writes status_since on every in-progress transition.
    row_stuck_after = get_handle("stuck", db_path=tmp_db)
    assert row_stuck_after["status_since"] is not None
    since = datetime.datetime.fromisoformat(row_stuck_after["status_since"].replace("Z", "+00:00"))
    assert abs((now - since).total_seconds()) < 5, "status_since must be updated on re-run"


# ---------------------------------------------------------------------------
# T6 — double-run guard (fresh status_since → skip, confirming T5(d/e) in isolation)
# ---------------------------------------------------------------------------

def test_t6_double_run_skipped(tmp_db: Path) -> None:
    from orchestration.runner import ingest_handle

    now = datetime.datetime.now(UTC)
    fresh_ts = _iso(now - datetime.timedelta(seconds=30))
    upsert_handle("testuser", {"status": "backfilling", "status_since": fresh_ts}, db_path=tmp_db)

    fake = FakeSource(pages=[[]])
    with _patch(fake):
        result = ingest_handle("testuser", provider="fake", db_path=tmp_db)

    assert result.outcome == "skipped"
    assert fake._call_count == 0
    print(f"\nT6: outcome={result.outcome}, adapter_calls={fake._call_count}")


# ---------------------------------------------------------------------------
# T7
# ---------------------------------------------------------------------------

def test_t7_ingest_all_isolation(tmp_db: Path) -> None:
    from orchestration.runner import ingest_all

    for h in ("alice", "bob", "carol"):
        upsert_handle(h, {"status": "pending"}, db_path=tmp_db)

    tweets_alice = [_tweet("a1", "2026-05-01T10:00:00Z")]
    tweets_carol = [_tweet("c1", "2026-05-02T10:00:00Z")]

    def fake_get_source(provider):
        class R:
            def fetch_user_info(self, handle): return FakeSource().fetch_user_info(handle)
            def fetch_tweets(self, handle, start, end):
                if handle == "bob": raise RuntimeError("broken")
                return tweets_alice if handle == "alice" else tweets_carol
        return R()

    with patch("orchestration.runner.get_source", side_effect=fake_get_source):
        results = ingest_all(provider="fake", db_path=tmp_db)

    by = {r.handle: r for r in results}
    print(f"\nT7: {[(r.handle, r.outcome) for r in results]}")
    assert by["alice"].outcome == "ok"
    assert by["bob"].outcome   == "failed"
    assert by["carol"].outcome == "ok"
    assert get_handle("alice", db_path=tmp_db)["status"] == "ready"
    assert get_handle("bob",   db_path=tmp_db)["status"] == "failed"
    assert get_handle("carol", db_path=tmp_db)["status"] == "ready"
