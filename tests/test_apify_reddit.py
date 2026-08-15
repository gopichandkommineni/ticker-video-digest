"""Tests for the Apify Reddit scraper + backend factory (HTTP mocked)."""
import time
from unittest.mock import MagicMock, patch

from core.social_media.base import SocialSignals
from core.social_media.reddit.apify_client import ApifyRedditScraper, _to_datetime


def test_to_datetime_epoch_and_iso():
    assert _to_datetime(1_600_000_000).year == 2020
    assert _to_datetime("2026-08-15T10:00:00Z").year == 2026
    assert _to_datetime(None) is None
    assert _to_datetime("not-a-date") is None


def test_unavailable_without_token(monkeypatch):
    monkeypatch.setattr("core.social_media.reddit.apify_client.APIFY_TOKEN", "")
    s = ApifyRedditScraper()
    s._token = ""
    assert s.is_available is False
    result = s.search_ticker("RKLB")
    assert isinstance(result, SocialSignals)
    assert result.posts == []


def test_maps_dataset_items_with_varied_field_names():
    now = time.time()
    items = [
        {  # trudax-style fields
            "dataType": "post", "id": "p1", "title": "RKLB Neutron DD",
            "body": "great writeup", "url": "https://reddit.com/r/x/p1",
            "upVotes": 4200, "numberOfComments": 318, "username": "dh",
            "parsedCommunityName": "wallstreetbets", "createdAt": now,
        },
        {  # alternate field names
            "type": "post", "postId": "p2", "title": "RKLB earnings",
            "selftext": "text", "link": "https://reddit.com/r/y/p2",
            "score": 150, "num_comments": 20, "author": "vg",
            "subreddit": "stocks", "created_utc": now,
        },
        {"dataType": "comment", "id": "c1", "body": "a comment"},  # skipped
    ]
    scraper = ApifyRedditScraper()
    scraper._token = "tok"

    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = items
    with patch("core.social_media.reddit.apify_client.requests.post", return_value=resp):
        result = scraper.search_ticker("RKLB", max_posts=10)

    ids = sorted(p.post_id for p in result.posts)
    assert ids == ["p1", "p2"]                    # comment skipped
    p1 = next(p for p in result.posts if p.post_id == "p1")
    assert p1.score == 4200 and p1.comment_count == 318
    assert p1.subreddit == "wallstreetbets" and p1.ticker == "RKLB"


def test_old_posts_filtered():
    scraper = ApifyRedditScraper()
    scraper._token = "tok"
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = [
        {"dataType": "post", "id": "old", "title": "x", "createdAt": "2020-01-01T00:00:00Z"},
    ]
    with patch("core.social_media.reddit.apify_client.requests.post", return_value=resp):
        result = scraper.search_ticker("RKLB", days_back=7)
    assert result.posts == []


def test_run_failure_returns_empty():
    scraper = ApifyRedditScraper()
    scraper._token = "tok"
    with patch("core.social_media.reddit.apify_client.requests.post", side_effect=RuntimeError("boom")):
        result = scraper.search_ticker("RKLB")
    assert result.posts == []


def test_verify_auth(monkeypatch):
    scraper = ApifyRedditScraper()
    scraper._token = "tok"
    resp = MagicMock(); resp.status_code = 200
    with patch("core.social_media.reddit.apify_client.requests.get", return_value=resp):
        ok, _ = scraper.verify_auth()
    assert ok is True

    resp.status_code = 401
    with patch("core.social_media.reddit.apify_client.requests.get", return_value=resp):
        ok, detail = scraper.verify_auth()
    assert ok is False and "rejected" in detail


# --- factory ---------------------------------------------------------------

def test_factory_prefers_apify_when_token_set(monkeypatch):
    from casino_dashboard.jobs.reddit_pull import make_reddit_scraper
    import core.config as cfg

    monkeypatch.delenv("REDDIT_BACKEND", raising=False)
    monkeypatch.setattr(cfg, "APIFY_TOKEN", "tok")
    assert make_reddit_scraper().__class__.__name__ == "ApifyRedditScraper"


def test_factory_defaults_to_arctic_shift(monkeypatch):
    from casino_dashboard.jobs.reddit_pull import make_reddit_scraper
    import core.config as cfg

    monkeypatch.delenv("REDDIT_BACKEND", raising=False)
    monkeypatch.setattr(cfg, "APIFY_TOKEN", "")
    assert make_reddit_scraper().__class__.__name__ == "ArcticShiftScraper"


def test_factory_backend_override(monkeypatch):
    from casino_dashboard.jobs.reddit_pull import make_reddit_scraper
    import core.config as cfg

    monkeypatch.setattr(cfg, "APIFY_TOKEN", "tok")  # present, but override wins
    monkeypatch.setenv("REDDIT_BACKEND", "direct")
    assert make_reddit_scraper().__class__.__name__ == "RedditScraper"
    monkeypatch.setenv("REDDIT_BACKEND", "arctic_shift")
    assert make_reddit_scraper().__class__.__name__ == "ArcticShiftScraper"
