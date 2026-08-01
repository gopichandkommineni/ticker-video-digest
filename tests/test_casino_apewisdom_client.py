"""Tests for apewisdom_client — all HTTP mocked."""
import json
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

import pytest

from core.social_media.reddit.apewisdom_client import (
    fetch_apewisdom_universe,
    filter_to_universe,
)
from casino_dashboard.data.models import ApeWisdomMention


def _make_page(results: list[dict]) -> bytes:
    return json.dumps({"results": results}).encode()


def _make_item(ticker: str, mentions: int = 10, ago: int = 5, upvotes: int = 20) -> dict:
    return {
        "ticker": ticker,
        "mentions": mentions,
        "mentions_24h_ago": ago,
        "upvotes": upvotes,
    }


# ── Single page ───────────────────────────────────────────────────────────────

def test_single_page_returns_correct_mentions():
    page1 = _make_page([_make_item("AAOI", 50, 25, 100), _make_item("RKLB", 30, 10, 60)])
    empty = _make_page([])

    responses = [page1, empty]
    call_idx = 0

    def fake_urlopen(req, timeout=None):
        nonlocal call_idx
        resp = MagicMock()
        resp.read.return_value = responses[call_idx]
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        call_idx += 1
        return resp

    with patch("core.social_media.reddit.apewisdom_client.urlopen", fake_urlopen):
        with patch("core.social_media.reddit.apewisdom_client.time.sleep"):
            result = fetch_apewisdom_universe("all-stocks")

    assert len(result) == 2
    tickers = {m.ticker for m in result}
    assert tickers == {"AAOI", "RKLB"}
    aaoi = next(m for m in result if m.ticker == "AAOI")
    assert aaoi.mentions == 50
    assert aaoi.mentions_24h_ago == 25
    assert aaoi.upvotes == 100


def test_multi_page_pagination_walks_all_pages():
    page1 = _make_page([_make_item("AAOI")])
    page2 = _make_page([_make_item("RKLB"), _make_item("ASTS")])
    empty = _make_page([])

    responses = [page1, page2, empty]
    call_idx = 0

    def fake_urlopen(req, timeout=None):
        nonlocal call_idx
        resp = MagicMock()
        resp.read.return_value = responses[call_idx]
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        call_idx += 1
        return resp

    with patch("core.social_media.reddit.apewisdom_client.urlopen", fake_urlopen):
        with patch("core.social_media.reddit.apewisdom_client.time.sleep"):
            result = fetch_apewisdom_universe("all-stocks")

    assert len(result) == 3
    assert {m.ticker for m in result} == {"AAOI", "RKLB", "ASTS"}


def test_empty_first_page_returns_empty_list():
    def fake_urlopen(req, timeout=None):
        resp = MagicMock()
        resp.read.return_value = _make_page([])
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    with patch("core.social_media.reddit.apewisdom_client.urlopen", fake_urlopen):
        result = fetch_apewisdom_universe("all-stocks")

    assert result == []


def test_429_retries_once_then_raises():
    exc = HTTPError(url="http://x", code=429, msg="Too Many Requests", hdrs={}, fp=None)

    with patch("core.social_media.reddit.apewisdom_client.urlopen", side_effect=exc):
        with patch("core.social_media.reddit.apewisdom_client.time.sleep"):
            with pytest.raises(HTTPError):
                fetch_apewisdom_universe("all-stocks")


def test_malformed_json_skips_page_and_continues():
    bad_json = b"not json {"
    empty = _make_page([])

    responses = [bad_json, empty]
    call_idx = 0

    def fake_urlopen(req, timeout=None):
        nonlocal call_idx
        resp = MagicMock()
        resp.read.return_value = responses[call_idx]
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        call_idx += 1
        return resp

    with patch("core.social_media.reddit.apewisdom_client.urlopen", fake_urlopen):
        with patch("core.social_media.reddit.apewisdom_client.time.sleep"):
            result = fetch_apewisdom_universe("all-stocks")

    # Bad page skipped → empty result (next page also empty → stops)
    assert result == []


# ── filter_to_universe ────────────────────────────────────────────────────────

def test_filter_to_universe_returns_only_matching_tickers():
    mentions = [
        ApeWisdomMention("AAOI", 50, 25, 100),
        ApeWisdomMention("RKLB", 30, 10, 60),
        ApeWisdomMention("TSLA", 200, 150, 500),
    ]
    result = filter_to_universe(mentions, {"AAOI", "RKLB"})
    assert len(result) == 2
    assert {m.ticker for m in result} == {"AAOI", "RKLB"}


def test_filter_to_universe_case_insensitive():
    mentions = [ApeWisdomMention("aaoi", 10, 5, 20)]
    result = filter_to_universe(mentions, {"AAOI"})
    assert len(result) == 1


def test_user_agent_header_set_correctly():
    """Verify the User-Agent is set on requests."""
    captured = []

    def fake_urlopen(req, timeout=None):
        captured.append(req.get_header("User-agent"))
        resp = MagicMock()
        resp.read.return_value = _make_page([])
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    with patch("core.social_media.reddit.apewisdom_client.urlopen", fake_urlopen):
        fetch_apewisdom_universe("all-stocks")

    assert len(captured) == 1
    assert "casino-dashboard" in captured[0]
