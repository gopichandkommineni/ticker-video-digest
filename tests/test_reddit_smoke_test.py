"""Tests for the read-only Reddit smoke-test module (mocked scraper)."""
from datetime import datetime, timezone
from unittest.mock import patch

from core.social_media.base import SocialPost, SocialSignals
from casino_dashboard.jobs import reddit_smoke_test as smoke


def _resolve(argv):
    return smoke._resolve_tickers(argv)


def test_resolve_from_argv():
    assert _resolve(["rklb", "asts"]) == ["RKLB", "ASTS"]


def test_resolve_from_env(monkeypatch):
    monkeypatch.setenv("REDDIT_SMOKE_TICKERS", "coin, hood ")
    assert _resolve([]) == ["COIN", "HOOD"]


def test_resolve_default(monkeypatch):
    monkeypatch.delenv("REDDIT_SMOKE_TICKERS", raising=False)
    assert _resolve([]) == smoke._DEFAULT_TICKERS


def test_run_builds_markdown_table():
    posts = [
        SocialPost(
            platform="reddit", post_id="p1", author="u", title="RKLB Neutron DD",
            content="c", url="https://reddit.com/r/x/p1/",
            published_at=datetime.now(tz=timezone.utc), score=500, comment_count=40,
            ticker="RKLB", subreddit="wallstreetbets",
        )
    ]

    class FakeScraper:
        _praw_reddit = None
        def auth_status(self):
            return "unauthenticated (public JSON API — Reddit blocks this for most IPs)"
        def search_ticker(self, ticker, days_back=7, max_posts=25, subreddits=None):
            if ticker == "RKLB":
                return SocialSignals(ticker=ticker, platform="reddit", posts=posts)
            return SocialSignals(ticker=ticker, platform="reddit", posts=[])

    with patch("casino_dashboard.jobs.reddit_smoke_test.RedditScraper", FakeScraper):
        lines = smoke.run(["RKLB", "EMPTY"])

    text = "\n".join(lines)
    assert "public JSON API" in text
    assert "No credentials" in text          # the unauthenticated warning
    assert "RKLB Neutron DD" in text
    assert "no posts in last 7d" in text      # EMPTY row


def test_run_verifies_auth_when_credentialed():
    class AuthedScraper:
        _praw_reddit = object()  # pretend credentials exist
        def auth_status(self):
            return "authenticated (read-only app-only OAuth)"
        def verify_auth(self):
            return True, "authenticated (read-only app-only OAuth)"
        def search_ticker(self, ticker, days_back=7, max_posts=25, subreddits=None):
            return SocialSignals(ticker=ticker, platform="reddit", posts=[])

    with patch("casino_dashboard.jobs.reddit_smoke_test.RedditScraper", AuthedScraper):
        lines = smoke.run(["RKLB"])

    text = "\n".join(lines)
    assert "Credential check: ✅" in text
    assert "authenticated" in text


def test_run_handles_fetch_error():
    class BoomScraper:
        _praw_reddit = None
        def auth_status(self):
            return "unauthenticated (public JSON API — Reddit blocks this for most IPs)"
        def search_ticker(self, *a, **k):
            raise RuntimeError("boom")

    with patch("casino_dashboard.jobs.reddit_smoke_test.RedditScraper", BoomScraper):
        lines = smoke.run(["RKLB"])
    assert any("error: boom" in ln for ln in lines)
