"""Unit tests for RedditScraper — no real network calls."""
from datetime import datetime, timezone
from unittest.mock import patch


from core.social_media.reddit.client import RedditScraper, _deduplicate
from core.social_media.base import SocialPost, SocialSignals



# ---------------------------------------------------------------------------
# Tests — SocialSignals computed properties
# ---------------------------------------------------------------------------

class TestSocialSignals:
    def _make_signal(self, scores: list[int]) -> SocialSignals:
        posts = [
            SocialPost(
                platform="reddit",
                post_id=str(i),
                author="u",
                content="text",
                url="https://reddit.com/r/x",
                published_at=datetime(2026, 5, 12, tzinfo=timezone.utc),
                score=s,
                ticker="RKLB",
            )
            for i, s in enumerate(scores)
        ]
        return SocialSignals(ticker="RKLB", platform="reddit", posts=posts)

    def test_total_posts(self):
        sig = self._make_signal([10, 20, 30])
        assert sig.total_posts == 3

    def test_avg_score(self):
        sig = self._make_signal([10, 20, 30])
        assert sig.avg_score == 20.0

    def test_avg_score_empty(self):
        sig = SocialSignals(ticker="RKLB", platform="reddit")
        assert sig.avg_score == 0.0

    def test_top_posts_ordered(self):
        sig = self._make_signal([5, 100, 50])
        assert sig.top_posts[0].score == 100


# ---------------------------------------------------------------------------
# Tests — helper functions
# ---------------------------------------------------------------------------

def test_deduplicate_removes_duplicates():
    p1 = SocialPost(
        platform="reddit", post_id="x1", author="a", content="c",
        url="u", published_at=datetime.utcnow(), ticker="T",
    )
    p2 = SocialPost(
        platform="reddit", post_id="x1", author="a", content="c",
        url="u", published_at=datetime.utcnow(), ticker="T",
    )
    assert len(_deduplicate([p1, p2])) == 1


def test_platform_name():
    s = RedditScraper()
    assert s.platform_name == "reddit"


def test_is_available():
    s = RedditScraper()
    assert s.is_available is False  # no PRAW credentials in the test env


# ---------------------------------------------------------------------------
# Tests — authenticated PRAW path
# ---------------------------------------------------------------------------

import sys
import types

from core.social_media.reddit import client as client_mod


def _fake_praw(calls: dict):
    mod = types.ModuleType("praw")

    class FakeReddit:
        def __init__(self, **kw):
            calls.update(kw)

    mod.Reddit = FakeReddit
    return mod


def test_praw_user_grant_and_ratelimit(monkeypatch):
    calls: dict = {}
    monkeypatch.setitem(sys.modules, "praw", _fake_praw(calls))
    monkeypatch.setattr(client_mod, "REDDIT_CLIENT_ID", "id")
    monkeypatch.setattr(client_mod, "REDDIT_CLIENT_SECRET", "sec")
    monkeypatch.setattr(client_mod, "REDDIT_USERNAME", "me")
    monkeypatch.setattr(client_mod, "REDDIT_PASSWORD", "pw")

    s = RedditScraper()
    assert s._praw_reddit is not None
    assert calls["username"] == "me" and calls["password"] == "pw"
    assert calls["ratelimit_seconds"] == 300
    assert s.auth_status().startswith("authenticated (user grant")


def test_praw_readonly_when_no_userpass(monkeypatch):
    calls: dict = {}
    monkeypatch.setitem(sys.modules, "praw", _fake_praw(calls))
    monkeypatch.setattr(client_mod, "REDDIT_CLIENT_ID", "id")
    monkeypatch.setattr(client_mod, "REDDIT_CLIENT_SECRET", "sec")
    monkeypatch.setattr(client_mod, "REDDIT_USERNAME", "")
    monkeypatch.setattr(client_mod, "REDDIT_PASSWORD", "")

    s = RedditScraper()
    assert s._praw_reddit is not None
    assert "username" not in calls and "password" not in calls
    assert s.auth_status() == "authenticated (read-only app-only OAuth)"


def test_auth_status_unauthenticated(monkeypatch):
    monkeypatch.setattr(client_mod, "REDDIT_CLIENT_ID", "")
    monkeypatch.setattr(client_mod, "REDDIT_CLIENT_SECRET", "")
    s = RedditScraper()
    assert s._praw_reddit is None
    assert "inactive" in s.auth_status()


def test_verify_auth_reports_failure(monkeypatch):
    monkeypatch.setattr(client_mod, "REDDIT_CLIENT_ID", "")
    monkeypatch.setattr(client_mod, "REDDIT_CLIENT_SECRET", "")
    s = RedditScraper()
    ok, detail = s.verify_auth()
    assert ok is False
    assert "no credentials" in detail
