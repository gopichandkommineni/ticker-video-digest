"""Tests for the shared Reddit HTTP config (User-Agent + proxy hooks)."""
from unittest.mock import MagicMock, patch

from core.social_media.reddit import _http


def test_default_user_agent(monkeypatch):
    monkeypatch.delenv("REDDIT_USER_AGENT", raising=False)
    ua = _http.reddit_user_agent()
    assert "casino-dashboard" in ua


def test_user_agent_override(monkeypatch):
    monkeypatch.setenv("REDDIT_USER_AGENT", "Mozilla/5.0 (custom)")
    assert _http.reddit_user_agent() == "Mozilla/5.0 (custom)"


def test_proxies_none_by_default(monkeypatch):
    monkeypatch.delenv("REDDIT_PROXY", raising=False)
    assert _http.reddit_proxy_url() is None
    assert _http.reddit_proxies() is None


def test_proxies_from_env(monkeypatch):
    monkeypatch.setenv("REDDIT_PROXY", "http://user:pass@proxy:8080")
    assert _http.reddit_proxy_url() == "http://user:pass@proxy:8080"
    assert _http.reddit_proxies() == {
        "http": "http://user:pass@proxy:8080",
        "https": "http://user:pass@proxy:8080",
    }


# --- wiring: proxy + UA actually reach the HTTP calls ---------------------

def test_scraper_public_path_passes_proxy_and_ua(monkeypatch):
    from core.social_media.reddit.client import RedditScraper

    monkeypatch.setenv("REDDIT_PROXY", "http://proxy:9000")
    monkeypatch.setenv("REDDIT_USER_AGENT", "test-agent/1.0")

    scraper = RedditScraper(subreddits=["stocks"])
    scraper._praw_reddit = None  # force public path

    resp = MagicMock()
    resp.json.return_value = {"data": {"children": []}}
    resp.raise_for_status.return_value = None

    with patch("core.social_media.reddit.client.requests.get", return_value=resp) as mock_get, \
         patch("core.social_media.reddit.client.time.sleep"):
        scraper.search_ticker("RKLB")

    _, kwargs = mock_get.call_args
    assert kwargs["proxies"] == {"http": "http://proxy:9000", "https": "http://proxy:9000"}
    assert kwargs["headers"]["User-Agent"] == "test-agent/1.0"


def test_discovery_about_passes_proxy(monkeypatch):
    from core.social_media.reddit import subreddit_discovery as sd

    monkeypatch.setenv("REDDIT_PROXY", "http://proxy:9000")
    resp = MagicMock()
    resp.status_code = 404
    with patch("core.social_media.reddit.subreddit_discovery.requests.get", return_value=resp) as mock_get:
        sd.fetch_about("RKLB")

    _, kwargs = mock_get.call_args
    assert kwargs["proxies"] == {"http": "http://proxy:9000", "https": "http://proxy:9000"}
