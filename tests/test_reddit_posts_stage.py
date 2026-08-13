"""Tests for the daily_refresh Reddit posts stage (mocked scraper, no network)."""
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from core.social_media.base import SocialPost, SocialSignals
from casino_dashboard.db.repository import get_recent_reddit_posts, get_social_history
from casino_dashboard.db.schema import init_db
from casino_dashboard.jobs.daily_refresh import _refresh_reddit_posts, _select_reddit_tickers


@pytest.fixture
def db(tmp_path: Path) -> Path:
    path = tmp_path / "test.db"
    init_db(path)
    return path


# ---------------------------------------------------------------------------
# _select_reddit_tickers
# ---------------------------------------------------------------------------

def test_priority_tickers_come_first_and_cap_applies():
    universe = ["AAA", "BBB", "CCC", "DDD"]
    selected = _select_reddit_tickers(universe, priority=["CCC", "AAA"], max_tickers=3)
    assert selected[:2] == ["CCC", "AAA"]  # priority order preserved
    assert len(selected) == 3
    assert len(set(selected)) == 3  # no duplicates


def test_priority_ticker_outside_universe_ignored():
    selected = _select_reddit_tickers(["AAA", "BBB"], priority=["ZZZ"], max_tickers=10)
    assert selected == ["AAA", "BBB"]


# ---------------------------------------------------------------------------
# _refresh_reddit_posts
# ---------------------------------------------------------------------------

def _signals(ticker: str, posts_spec: list[tuple[str, str, int]]) -> SocialSignals:
    posts = [
        SocialPost(
            platform="reddit",
            post_id=pid,
            author="u",
            title=f"{ticker} post {pid}",
            content="c",
            url=f"https://reddit.com/r/{sub}/comments/{pid}/",
            published_at=datetime.now(tz=timezone.utc),
            score=score,
            comment_count=5,
            ticker=ticker,
            subreddit=sub,
        )
        for pid, sub, score in posts_spec
    ]
    return SocialSignals(ticker=ticker, platform="reddit", posts=posts)


def test_stage_saves_posts_and_per_subreddit_aggregates(db: Path):
    fake = {
        "RKLB": _signals("RKLB", [("p1", "wallstreetbets", 400), ("p2", "wallstreetbets", 100), ("p3", "stocks", 50)]),
        "ASTS": _signals("ASTS", [("q1", "stocks", 20)]),
    }

    class FakeScraper:
        _praw_reddit = None
        def search_ticker(self, ticker, days_back=7, max_posts=25, subreddits=None):
            return fake.get(ticker, _signals(ticker, []))

    with patch("casino_dashboard.jobs.reddit_pull.RedditScraper", FakeScraper), \
         patch.dict("os.environ", {"REDDIT_POSTS_MAX_TICKERS": "10"}):
        total, covered = _refresh_reddit_posts(
            ["RKLB", "ASTS"], priority=["RKLB"], today=date(2026, 8, 13), db_path=db
        )

    assert total == 4
    assert covered == 2

    # Posts persisted
    assert len(get_recent_reddit_posts("RKLB", db_path=db)) == 3
    assert len(get_recent_reddit_posts("ASTS", db_path=db)) == 1

    # Per-subreddit aggregate rows written under source='reddit' with non-empty
    # subreddit, so they DON'T pollute the ApeWisdom (subreddit='') queries.
    assert get_social_history("RKLB", "reddit", 30, db).empty  # filters subreddit=''
    assert get_social_history("RKLB", "apewisdom", 30, db).empty


def test_stage_skips_when_max_tickers_zero(db: Path):
    class FakeScraper:
        _praw_reddit = None
        def search_ticker(self, *a, **k):  # pragma: no cover - must not be called
            raise AssertionError("should not fetch when disabled")

    with patch("casino_dashboard.jobs.reddit_pull.RedditScraper", FakeScraper), \
         patch.dict("os.environ", {"REDDIT_POSTS_MAX_TICKERS": "0"}):
        total, covered = _refresh_reddit_posts(
            ["RKLB"], priority=[], today=date(2026, 8, 13), db_path=db
        )
    assert (total, covered) == (0, 0)


def test_stage_survives_per_ticker_failure(db: Path):
    class FlakyScraper:
        _praw_reddit = None
        def search_ticker(self, ticker, days_back=7, max_posts=25, subreddits=None):
            if ticker == "BAD":
                raise RuntimeError("429 rate limited")
            return _signals(ticker, [("ok1", "stocks", 10)])

    with patch("casino_dashboard.jobs.reddit_pull.RedditScraper", FlakyScraper), \
         patch.dict("os.environ", {"REDDIT_POSTS_MAX_TICKERS": "10"}):
        total, covered = _refresh_reddit_posts(
            ["BAD", "GOOD"], priority=[], today=date(2026, 8, 13), db_path=db
        )

    assert total == 1  # BAD skipped, GOOD saved
    assert covered == 1
    assert len(get_recent_reddit_posts("GOOD", db_path=db)) == 1
