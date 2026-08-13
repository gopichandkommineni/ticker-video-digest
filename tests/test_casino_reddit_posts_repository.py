"""Tests for the reddit_posts repository methods."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from core.social_media.base import SocialPost
from casino_dashboard.db.repository import get_recent_reddit_posts, save_reddit_posts
from casino_dashboard.db.schema import init_db


@pytest.fixture
def db(tmp_path: Path) -> Path:
    path = tmp_path / "test.db"
    init_db(path)
    return path


def _post(post_id: str, ticker: str = "RKLB", score: int = 100, age_days: int = 1, **kw) -> SocialPost:
    published = datetime.now(tz=timezone.utc) - timedelta(days=age_days)
    defaults = dict(
        platform="reddit",
        post_id=post_id,
        author="user1",
        title=f"{ticker} DD",
        content="body text",
        url=f"https://reddit.com/r/stocks/comments/{post_id}/",
        published_at=published,
        score=score,
        comment_count=12,
        ticker=ticker,
        subreddit="stocks",
    )
    defaults.update(kw)
    return SocialPost(**defaults)


def test_save_and_get_roundtrip(db: Path):
    saved = save_reddit_posts([_post("a1"), _post("a2", score=500)], db)
    assert saved == 2
    df = get_recent_reddit_posts("RKLB", days=7, db_path=db)
    assert len(df) == 2
    # newest-first ordering is by published_at desc; both present with fields intact
    assert set(df["post_id"]) == {"a1", "a2"}
    assert df["score"].max() == 500


def test_save_empty_is_noop(db: Path):
    assert save_reddit_posts([], db) == 0
    assert get_recent_reddit_posts("RKLB", db_path=db).empty


def test_idempotent_replace_on_post_id_ticker(db: Path):
    save_reddit_posts([_post("dup", score=10)], db)
    save_reddit_posts([_post("dup", score=999)], db)  # same (post_id, ticker)
    df = get_recent_reddit_posts("RKLB", db_path=db)
    assert len(df) == 1
    assert int(df.iloc[0]["score"]) == 999  # overwritten, not duplicated


def test_same_post_under_two_tickers_kept(db: Path):
    save_reddit_posts([_post("shared", ticker="RKLB"), _post("shared", ticker="ASTS")], db)
    assert len(get_recent_reddit_posts("RKLB", db_path=db)) == 1
    assert len(get_recent_reddit_posts("ASTS", db_path=db)) == 1


def test_old_posts_excluded_by_window(db: Path):
    save_reddit_posts([_post("recent", age_days=1), _post("stale", age_days=40)], db)
    df = get_recent_reddit_posts("RKLB", days=7, db_path=db)
    assert list(df["post_id"]) == ["recent"]
