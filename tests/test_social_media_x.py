"""Unit tests for XScraper — no real network calls."""
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from core.social_media.x.client import XScraper
from core.social_media.base import SocialSignals


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _api_response(tweets: list[dict], next_token: str | None = None) -> dict:
    meta: dict = {"result_count": len(tweets)}
    if next_token:
        meta["next_token"] = next_token
    return {
        "data": tweets,
        "includes": {
            "users": [{"id": "u1", "username": "trader_joe"}],
        },
        "meta": meta,
    }


def _tweet(tid: str = "t1", author_id: str = "u1", text: str = "$RKLB to moon") -> dict:
    return {
        "id": tid,
        "author_id": author_id,
        "text": text,
        "created_at": "2026-05-12T10:00:00Z",
        "public_metrics": {"like_count": 55, "reply_count": 3},
    }


# ---------------------------------------------------------------------------
# Tests — credentials missing
# ---------------------------------------------------------------------------

class TestXScraperNoCredentials:
    def setup_method(self):
        with patch("core.social_media.x.client.X_BEARER_TOKEN", ""):
            self.scraper = XScraper()

    def test_is_available_false(self):
        with patch("core.social_media.x.client.X_BEARER_TOKEN", ""):
            scraper = XScraper()
            assert not scraper.is_available

    @patch("core.social_media.x.client.X_BEARER_TOKEN", "")
    def test_returns_empty_signals_when_no_token(self):
        scraper = XScraper()
        result = scraper.search_ticker("RKLB")
        assert isinstance(result, SocialSignals)
        assert result.posts == []
        assert result.platform == "x"


# ---------------------------------------------------------------------------
# Tests — successful fetch
# ---------------------------------------------------------------------------

class TestXScraperWithCredentials:
    def setup_method(self):
        with patch("core.social_media.x.client.X_BEARER_TOKEN", "fake-token"):
            self.scraper = XScraper()

    @patch("core.social_media.x.client.X_BEARER_TOKEN", "fake-token")
    @patch("core.social_media.x.client.requests.get")
    def test_returns_social_signals(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = _api_response([_tweet()])
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        result = self.scraper.search_ticker("RKLB")
        assert isinstance(result, SocialSignals)
        assert result.platform == "x"
        assert len(result.posts) == 1

    @patch("core.social_media.x.client.X_BEARER_TOKEN", "fake-token")
    @patch("core.social_media.x.client.requests.get")
    def test_post_fields_populated(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = _api_response([_tweet(tid="t99")])
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        result = self.scraper.search_ticker("RKLB")
        post = result.posts[0]

        assert post.post_id == "t99"
        assert post.author == "trader_joe"
        assert post.score == 55
        assert post.comment_count == 3
        assert "x.com" in post.url
        assert post.ticker == "RKLB"
        assert post.title is None  # X has no titles

    @patch("core.social_media.x.client.X_BEARER_TOKEN", "fake-token")
    @patch("core.social_media.x.client.requests.get")
    def test_pagination_stops_on_no_next_token(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = _api_response([_tweet()])
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        result = self.scraper.search_ticker("RKLB", max_posts=50)
        assert mock_get.call_count == 1  # only one page needed

    @patch("core.social_media.x.client.X_BEARER_TOKEN", "fake-token")
    @patch("core.social_media.x.client.requests.get")
    def test_http_error_returns_partial_results(self, mock_get):
        import requests as req_lib

        good = MagicMock()
        good.json.return_value = _api_response([_tweet("t1")], next_token="tok")
        good.raise_for_status.return_value = None

        bad = MagicMock()
        bad.raise_for_status.side_effect = req_lib.HTTPError("429")

        mock_get.side_effect = [good, bad]

        result = self.scraper.search_ticker("RKLB", max_posts=200)
        assert len(result.posts) == 1  # first page succeeded

    @patch("core.social_media.x.client.X_BEARER_TOKEN", "fake-token")
    @patch("core.social_media.x.client.requests.get")
    def test_unknown_author_falls_back_to_id(self, mock_get):
        tweet = _tweet(tid="t2", author_id="unknown_id")
        mock_resp = MagicMock()
        mock_resp.json.return_value = _api_response([tweet])
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        result = self.scraper.search_ticker("RKLB")
        assert result.posts[0].author == "unknown_id"


def test_platform_name():
    s = XScraper()
    assert s.platform_name == "x"
