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


# --- impersonation selection ---------------------------------------------

def test_impersonate_default_chrome(monkeypatch):
    monkeypatch.delenv("REDDIT_IMPERSONATE", raising=False)
    assert _http.reddit_impersonate() == "chrome"


def test_impersonate_can_be_disabled(monkeypatch):
    for off in ("none", "off", "", "0", "False"):
        monkeypatch.setenv("REDDIT_IMPERSONATE", off)
        assert _http.reddit_impersonate() is None


# --- reddit_get: browser-impersonating fetch ------------------------------

def test_reddit_get_uses_curl_cffi_with_impersonate_proxy_ua(monkeypatch):
    monkeypatch.delenv("REDDIT_IMPERSONATE", raising=False)   # default chrome
    monkeypatch.setenv("REDDIT_PROXY", "http://proxy:9000")
    monkeypatch.setenv("REDDIT_USER_AGENT", "test-agent/1.0")

    import curl_cffi.requests as cffi
    with patch.object(cffi, "get", return_value=MagicMock()) as mock_get:
        _http.reddit_get("https://www.reddit.com/r/stocks/about.json", params={"q": "x"})

    _, kwargs = mock_get.call_args
    assert kwargs["impersonate"] == "chrome"
    assert kwargs["proxies"] == {"http": "http://proxy:9000", "https": "http://proxy:9000"}
    assert kwargs["headers"] == {"User-Agent": "test-agent/1.0"}
    assert kwargs["params"] == {"q": "x"}


def test_reddit_get_impersonate_supplies_browser_ua_when_unset(monkeypatch):
    monkeypatch.delenv("REDDIT_IMPERSONATE", raising=False)
    monkeypatch.delenv("REDDIT_USER_AGENT", raising=False)

    import curl_cffi.requests as cffi
    with patch.object(cffi, "get", return_value=MagicMock()) as mock_get:
        _http.reddit_get("https://www.reddit.com/r/stocks/about.json")

    _, kwargs = mock_get.call_args
    # No explicit UA -> None, letting curl_cffi's impersonation set a matching one.
    assert kwargs["headers"] is None


def test_reddit_get_falls_back_to_requests_when_disabled(monkeypatch):
    monkeypatch.setenv("REDDIT_IMPERSONATE", "none")
    monkeypatch.delenv("REDDIT_USER_AGENT", raising=False)

    import requests
    with patch.object(requests, "get", return_value=MagicMock()) as mock_get:
        _http.reddit_get("https://www.reddit.com/r/stocks/about.json")

    _, kwargs = mock_get.call_args
    assert "impersonate" not in kwargs
    assert kwargs["headers"]["User-Agent"]  # a UA is always sent on the plain path
