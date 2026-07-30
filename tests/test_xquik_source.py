"""Offline contract tests for the Xquik tweet-source adapter."""

from __future__ import annotations

import datetime
import io
import json
import urllib.error
from unittest.mock import patch

import pytest

from tweet_sources.base import ServerError
from tweet_sources.factory import get_source
from tweet_sources.xquik import XquikSource


def _tweet(tweet_id: str = "1790000000000000000") -> dict:
    return {
        "id": tweet_id,
        "text": "$RKLB launch thread",
        "createdAt": "2026-07-01T12:00:00.123Z",
        "isReply": False,
        "isQuoteStatus": False,
        "likeCount": 12,
        "retweetCount": 3,
        "replyCount": 2,
        "quoteCount": 1,
        "viewCount": 1200,
        "bookmarkCount": 4,
        "url": f"https://x.com/trader/status/{tweet_id}",
        "author": {
            "id": "u1",
            "username": "trader",
            "name": "Trader",
            "followers": 100,
            "following": 5,
            "description": "markets",
            "verified": True,
            "isBlueVerified": True,
            "createdAt": "2020-01-01T00:00:00Z",
        },
        "media": [{"mediaUrl": "https://pbs.twimg.com/media/example.jpg"}],
    }


@patch("tweet_sources.xquik.get_json")
def test_fetch_tweets_maps_search_response(mock_get_json) -> None:
    mock_get_json.return_value = {
        "tweets": [_tweet()],
        "has_next_page": False,
        "next_cursor": "",
    }

    result = XquikSource("key").fetch_tweets(
        "trader",
        datetime.date(2026, 7, 1),
        datetime.date(2026, 7, 1),
    )

    assert result.reached_floor is True
    assert result.skipped == 0
    assert len(result.tweets) == 1
    tweet = result.tweets[0]
    assert tweet.id == "1790000000000000000"
    assert tweet.created_at_utc == "2026-07-01T12:00:00Z"
    assert tweet.text == "$RKLB launch thread"
    assert tweet.like_count == 12
    assert tweet.media_urls == ["https://pbs.twimg.com/media/example.jpg"]
    called_url = mock_get_json.call_args.args[0]
    assert "/api/v1/x/tweets/search" in called_url
    assert "from%3Atrader" in called_url
    assert "until%3A2026-07-02" in called_url
    assert mock_get_json.call_args.args[1] == {"X-API-Key": "key"}


@patch("tweet_sources.xquik.get_json")
def test_fetch_tweets_follows_cursor_after_empty_page(mock_get_json) -> None:
    mock_get_json.side_effect = [
        {
            "tweets": [],
            "has_next_page": True,
            "next_cursor": "next",
        },
        {
            "tweets": [_tweet()],
            "has_next_page": False,
            "next_cursor": "",
        },
    ]

    result = XquikSource("key").fetch_tweets(
        "trader",
        datetime.date(2026, 7, 1),
        datetime.date(2026, 7, 1),
    )

    assert result.reached_floor is True
    assert [tweet.id for tweet in result.tweets] == ["1790000000000000000"]
    assert mock_get_json.call_count == 2
    assert "cursor=next" in mock_get_json.call_args.args[0]


@patch("tweet_sources.xquik.get_json")
def test_fetch_user_info_uses_profile_endpoint(mock_get_json) -> None:
    author = _tweet()["author"]
    author["verified"] = False
    author["isVerified"] = True
    mock_get_json.return_value = author

    info = XquikSource("key").fetch_user_info("@trader")

    assert info.handle == "trader"
    assert info.user_id == "u1"
    assert info.followers_count == 100
    assert info.is_verified is True
    assert info.is_blue_verified is True
    assert mock_get_json.call_args.args[0].endswith("/api/v1/x/users/trader")


def test_dependency_failure_is_transient() -> None:
    response = io.BytesIO(json.dumps({"error": "x_api_unavailable"}).encode())
    error = urllib.error.HTTPError(
        url="https://xquik.com/api/v1/x/users/trader",
        code=424,
        msg="Failed Dependency",
        hdrs=None,
        fp=response,
    )

    with patch("urllib.request.urlopen", side_effect=error):
        with pytest.raises(ServerError) as raised:
            XquikSource("key").fetch_user_info("trader")

    assert raised.value.status_code == 424


@patch("tweet_sources.xquik.get_json")
def test_invalid_handle_does_not_request_paid_data(mock_get_json) -> None:
    with pytest.raises(ValueError, match="Invalid X handle"):
        XquikSource("key").fetch_tweets(
            "trader from:other",
            datetime.date(2026, 7, 1),
            datetime.date(2026, 7, 1),
        )

    mock_get_json.assert_not_called()


def test_factory_returns_xquik_source(monkeypatch) -> None:
    monkeypatch.setenv("XQUIK_API_KEY", "key")

    source = get_source("xquik")

    assert isinstance(source, XquikSource)


def test_factory_requires_xquik_api_key(monkeypatch) -> None:
    monkeypatch.delenv("XQUIK_API_KEY", raising=False)

    with pytest.raises(EnvironmentError, match="XQUIK_API_KEY is not set"):
        get_source("xquik")
