"""Tests for the shared Reddit pull-and-store logic (mocked scraper, no network)."""
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from core.social_media.base import SocialPost, SocialSignals
from casino_dashboard.db.repository import get_recent_reddit_posts
from casino_dashboard.db.schema import init_db
from casino_dashboard.jobs.reddit_pull import pull_reddit_for_tickers, save_ticker_signals


@pytest.fixture
def db(tmp_path: Path) -> Path:
    path = tmp_path / "test.db"
    init_db(path)
    return path


def _signals(ticker, specs):
    posts = [
        SocialPost(
            platform="reddit", post_id=pid, author="u", title=f"{ticker} {pid}",
            content="c", url=f"https://reddit.com/r/{sub}/{pid}/",
            published_at=datetime.now(tz=timezone.utc), score=score, comment_count=1,
            ticker=ticker, subreddit=sub,
        )
        for pid, sub, score in specs
    ]
    return SocialSignals(ticker=ticker, platform="reddit", posts=posts)


class _Scraper:
    """Records the subreddits override it was called with, per ticker."""
    _praw_reddit = None

    def __init__(self, data):
        self.data = data
        self.calls: dict[str, list | None] = {}

    def search_ticker(self, ticker, days_back=7, max_posts=25, subreddits=None):
        self.calls[ticker] = subreddits
        return self.data.get(ticker, _signals(ticker, []))


def test_pull_uses_map_subreddits_and_falls_back(db: Path):
    scraper = _Scraper({
        "RKLB": _signals("RKLB", [("p1", "RocketLab", 100)]),
        "ASTS": _signals("ASTS", [("q1", "stocks", 10)]),
    })
    smap = {"RKLB": ["RocketLab", "RKLB"]}  # ASTS not in map -> default subs

    total, covered = pull_reddit_for_tickers(
        ["RKLB", "ASTS"], date(2026, 8, 13), db, subreddit_map=smap, scraper=scraper
    )

    assert (total, covered) == (2, 2)
    assert scraper.calls["RKLB"] == ["RocketLab", "RKLB"]  # map applied
    assert scraper.calls["ASTS"] is None                    # fell back to defaults
    assert len(get_recent_reddit_posts("RKLB", db_path=db)) == 1


def test_pull_survives_failure(db: Path):
    class Flaky(_Scraper):
        def search_ticker(self, ticker, days_back=7, max_posts=25, subreddits=None):
            if ticker == "BAD":
                raise RuntimeError("boom")
            return _signals(ticker, [("ok", "stocks", 5)])

    total, covered = pull_reddit_for_tickers(
        ["BAD", "GOOD"], date(2026, 8, 13), db, scraper=Flaky({})
    )
    assert (total, covered) == (1, 1)


def test_save_ticker_signals_empty_is_noop(db: Path):
    assert save_ticker_signals("RKLB", _signals("RKLB", []), date(2026, 8, 13), db) == 0
