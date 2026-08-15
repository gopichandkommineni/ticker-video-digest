"""Unit tests for RedditScraper — no real network calls."""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from core.social_media.reddit.client import RedditScraper, _deduplicate
from core.social_media.base import SocialPost, SocialSignals


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_post(**overrides) -> dict:
    defaults = {
        "id": "abc123",
        "author": "user1",
        "title": "RKLB to the moon",
        "selftext": "Rocket Lab is looking great this week.",
        "permalink": "/r/stocks/comments/abc123/rklb/",
        "score": 420,
        "num_comments": 37,
        # Relative to now so the days_back=7 filter always treats it as recent
        # (a hardcoded date turns these into time-bombs as the clock advances).
        "created_utc": (datetime.now(tz=timezone.utc) - timedelta(days=2)).timestamp(),
    }
    return {**defaults, **overrides}


def _reddit_json_response(posts: list[dict]) -> dict:
    return {
        "data": {
            "children": [{"data": p} for p in posts],
        }
    }


# ---------------------------------------------------------------------------
# Tests — public JSON API path
# ---------------------------------------------------------------------------

class TestRedditScraperPublicAPI:
    def setup_method(self):
        # Force public API by making PRAW unavailable
        with patch("core.social_media.reddit.client.REDDIT_CLIENT_ID", ""):
            with patch("core.social_media.reddit.client.REDDIT_CLIENT_SECRET", ""):
                self.scraper = RedditScraper(subreddits=["stocks"])
        assert self.scraper._praw_reddit is None

    @patch("core.social_media.reddit.client.reddit_get")
    @patch("core.social_media.reddit.client.time.sleep")
    def test_returns_social_signals(self, mock_sleep, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = _reddit_json_response([_make_post()])
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        result = self.scraper.search_ticker("RKLB", days_back=7, max_posts=10)

        assert isinstance(result, SocialSignals)
        assert result.ticker == "RKLB"
        assert result.platform == "reddit"
        assert len(result.posts) == 1

    @patch("core.social_media.reddit.client.reddit_get")
    @patch("core.social_media.reddit.client.time.sleep")
    def test_post_fields_populated(self, mock_sleep, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = _reddit_json_response([_make_post(score=999)])
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        result = self.scraper.search_ticker("RKLB")
        post = result.posts[0]

        assert post.platform == "reddit"
        assert post.score == 999
        assert post.ticker == "RKLB"
        assert post.subreddit == "stocks"
        assert "reddit.com" in post.url

    @patch("core.social_media.reddit.client.reddit_get")
    @patch("core.social_media.reddit.client.time.sleep")
    def test_filters_old_posts(self, mock_sleep, mock_get):
        old_post = _make_post(
            id="old1",
            created_utc=datetime(2020, 1, 1, tzinfo=timezone.utc).timestamp(),
        )
        mock_resp = MagicMock()
        mock_resp.json.return_value = _reddit_json_response([old_post])
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        result = self.scraper.search_ticker("RKLB", days_back=7)
        assert len(result.posts) == 0

    @patch("core.social_media.reddit.client.reddit_get")
    @patch("core.social_media.reddit.client.time.sleep")
    def test_http_error_returns_empty(self, mock_sleep, mock_get):
        import requests as req_lib
        mock_get.side_effect = req_lib.HTTPError("403")

        result = self.scraper.search_ticker("RKLB")
        assert result.posts == []

    @patch("core.social_media.reddit.client.reddit_get")
    @patch("core.social_media.reddit.client.time.sleep")
    def test_deduplicates_across_subreddits(self, mock_sleep, mock_get):
        scraper = RedditScraper(subreddits=["stocks", "investing"])
        scraper._praw_reddit = None

        same_post = _make_post(id="dup1")
        mock_resp = MagicMock()
        mock_resp.json.return_value = _reddit_json_response([same_post])
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        result = scraper.search_ticker("RKLB")
        assert len(result.posts) == 1


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
    assert s.is_available is True  # public API always available
