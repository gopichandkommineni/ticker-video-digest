"""Tests for the Arctic Shift client + discovery integration (HTTP mocked).

Payloads mirror Arctic Shift's documented shape: {"data": [ ...items... ]}.
"""
import time

import pytest
from unittest.mock import MagicMock, patch

from core.social_media.base import SocialSignals
from core.social_media.reddit import arctic_shift_client as arctic
from core.social_media.reddit.arctic_shift_client import ArcticShiftScraper, _to_post


def _resp(status=200, payload=None):
    m = MagicMock()
    m.status_code = status
    m.headers = {}
    m.json.return_value = payload if payload is not None else {"data": []}
    return m


def _post(pid, sub, score, ncomments, age_days=1, title="RKLB DD"):
    return {
        "id": pid, "subreddit": sub, "title": title, "selftext": "body",
        "score": score, "num_comments": ncomments, "author": "u",
        "permalink": f"/r/{sub}/comments/{pid}/x/",
        "created_utc": time.time() - age_days * 86400,
    }


# --- low-level parsing -----------------------------------------------------

def test_to_post_maps_fields():
    p = _to_post(_post("a1", "wallstreetbets", 400, 30), "RKLB")
    assert p.post_id == "a1" and p.score == 400 and p.comment_count == 30
    assert p.subreddit == "wallstreetbets" and p.ticker == "RKLB"
    assert "reddit.com/r/wallstreetbets" in p.url


def test_to_post_rejects_missing_fields():
    assert _to_post({"subreddit": "x"}, "RKLB") is None  # no id/created


def test_get_tolerates_bare_list_and_dict():
    with patch("core.social_media.reddit.arctic_shift_client.requests.get",
               return_value=_resp(payload=[{"id": "x"}])):
        assert arctic._get("http://u", {}) == [{"id": "x"}]
    with patch("core.social_media.reddit.arctic_shift_client.requests.get",
               return_value=_resp(payload={"data": [{"id": "y"}]})):
        assert arctic._get("http://u", {}) == [{"id": "y"}]


# --- scraper ---------------------------------------------------------------

def test_search_ticker_pulls_and_dedupes():
    scraper = ArcticShiftScraper(subreddits=["wallstreetbets", "stocks"])
    # Same post id returned from both subs -> deduped to one.
    payload = {"data": [_post("dup", "wallstreetbets", 100, 5),
                        _post("p2", "wallstreetbets", 50, 2)]}
    with patch("core.social_media.reddit.arctic_shift_client.requests.get",
               return_value=_resp(payload=payload)):
        result = scraper.search_ticker("RKLB", max_posts=10)
    assert isinstance(result, SocialSignals)
    assert sorted(p.post_id for p in result.posts) == ["dup", "p2"]


def test_search_ticker_empty_on_error():
    scraper = ArcticShiftScraper(subreddits=["stocks"])
    with patch("core.social_media.reddit.arctic_shift_client.requests.get",
               side_effect=Exception("down")):
        result = scraper.search_ticker("RKLB")
    assert result.posts == []


def test_verify_auth():
    scraper = ArcticShiftScraper()
    with patch("core.social_media.reddit.arctic_shift_client.requests.get", return_value=_resp(200)):
        ok, _ = scraper.verify_auth()
    assert ok is True
    with patch("core.social_media.reddit.arctic_shift_client.requests.get", return_value=_resp(503)):
        ok, _ = scraper.verify_auth()
    assert ok is False


def test_search_subreddits_uses_prefix_not_query():
    # Regression: /api/subreddits/search has no 'query' param (400). The fuzzy
    # lookup must send 'subreddit_prefix'.
    captured = {}

    def fake_get(url, params=None, headers=None, timeout=None):
        captured.update(params or {})
        return _resp(payload={"data": []})

    with patch("core.social_media.reddit.arctic_shift_client.requests.get", side_effect=fake_get):
        arctic.search_subreddits(query="rocket")
    assert captured.get("subreddit_prefix") == "rocket"
    assert "query" not in captured


def test_count_posts_in_window():
    payload = {"data": [_post(f"p{i}", "stocks", 1, 0) for i in range(7)]}
    with patch("core.social_media.reddit.arctic_shift_client.requests.get",
               return_value=_resp(payload=payload)):
        assert arctic.count_posts_in_window("stocks", days=7) == 7


# --- discovery now sourced from Arctic Shift -------------------------------

def test_discovery_ranks_via_arctic_shift():
    from core.social_media.reddit import subreddit_discovery as sd

    subs_data = {
        "RKLB": {"display_name": "RKLB", "subscribers": 15000,
                 "public_description": "RKLB Rocket Lab stock"},
        "RocketLab": {"display_name": "RocketLab", "subscribers": 42000,
                      "public_description": "Rocket Lab discussion"},
    }

    def fake_search_subreddits(query=None, subreddit=None, limit=20):
        if subreddit:  # fetch_about — exact lookup
            d = subs_data.get(subreddit)
            return [d] if d else []
        # search — return the name-based community
        return [subs_data["RocketLab"]]

    def fake_count(name, days=7):
        return {"RKLB": 12, "RocketLab": 40}.get(name, 0)

    with patch("core.social_media.reddit.arctic_shift_client.search_subreddits", side_effect=fake_search_subreddits), \
         patch("core.social_media.reddit.arctic_shift_client.count_posts_in_window", side_effect=fake_count):
        result = sd.discover("RKLB", company_name="Rocket Lab", sleep=False)

    names = [s.info.name for s in result.subreddits]
    assert "RKLB" in names and "RocketLab" in names
    assert result.found is True
    assert all(s.selected for s in result.subreddits)  # both real communities
    # subscriber + post-count metrics flowed through from Arctic Shift
    rklb = next(s for s in result.subreddits if s.info.name == "RKLB")
    assert rklb.info.subscribers == 15000 and rklb.info.posts_7d == 12
    rl = next(s for s in result.subreddits if s.info.name == "RocketLab")
    assert rl.info.subscribers == 42000 and rl.info.posts_7d == 40


# ---------------------------------------------------------------------------
# Subscriber-ranked enumeration (moved here when subreddit_rank_scan's job was
# folded into subreddit_catalog_run — the iterator itself lives on).
# ---------------------------------------------------------------------------

def _fake_ranked_search(dataset):
    """Mimic /api/subreddits/search sorted by subscribers desc, with min/max."""
    def fake(query=None, subreddit=None, limit=20, min_subscribers=None,
             max_subscribers=None, after=None, before=None, sort=None, sort_type=None):
        items = [
            d for d in dataset
            if (min_subscribers is None or d["subscribers"] >= min_subscribers)
            and (max_subscribers is None or d["subscribers"] <= max_subscribers)
        ]
        items.sort(key=lambda d: d["subscribers"], reverse=True)
        return (200, items[:limit])
    return fake


def test_iter_pages_descending_and_respects_floor():
    data = [{"display_name": n, "subscribers": s} for n, s in
            [("AAA", 500), ("BBB", 400), ("CCC", 300), ("DDD", 200), ("EEE", 150), ("FFF", 50)]]
    with patch.object(arctic, "search_subreddits_raw", side_effect=_fake_ranked_search(data)):
        out = list(arctic.iter_subreddits_by_subscribers(
            min_subscribers=100, max_count=100, page_size=2, sleep=0))
    names = [d["display_name"] for d in out]
    assert names == ["AAA", "BBB", "CCC", "DDD", "EEE"]   # FFF below floor; strictly descending


def test_iter_dedupes_and_caps_at_max_count():
    data = [{"display_name": n, "subscribers": s} for n, s in
            [("AAA", 500), ("BBB", 400), ("CCC", 300), ("DDD", 200)]]
    with patch.object(arctic, "search_subreddits_raw", side_effect=_fake_ranked_search(data)):
        out = list(arctic.iter_subreddits_by_subscribers(
            min_subscribers=1, max_count=3, page_size=2, sleep=0))
    assert [d["display_name"] for d in out] == ["AAA", "BBB", "CCC"]   # capped, no dupes


def test_iter_stops_when_empty():
    with patch.object(arctic, "search_subreddits_raw", return_value=(200, [])):
        out = list(arctic.iter_subreddits_by_subscribers(min_subscribers=1, sleep=0))
    assert out == []


def test_iter_raises_when_the_archive_rejects_subscriber_ranking():
    """A 400 on page 1 must not read as 'Reddit has no subreddits'."""
    with patch.object(arctic, "search_subreddits_raw", return_value=(400, [])):
        with pytest.raises(arctic.SubscriberSortUnsupported):
            list(arctic.iter_subreddits_by_subscribers(min_subscribers=1, sleep=0))
