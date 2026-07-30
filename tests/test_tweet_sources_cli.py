"""Regression tests for the tweet-source command line interface."""

from __future__ import annotations

import datetime
from argparse import Namespace
from unittest.mock import Mock, patch

from tweet_sources.__main__ import cmd_tweets
from tweet_sources.base import FetchResult, Tweet


def _tweet() -> Tweet:
    return Tweet(
        id="1790000000000000000",
        created_at_utc="2026-07-01T12:00:00Z",
        text="$RKLB launch",
        type="original",
        is_reply=False,
        is_quote=False,
        in_reply_to_id=None,
        quoted_tweet_id=None,
        quoted_author_id=None,
        conversation_id=None,
        like_count=1,
        retweet_count=2,
        reply_count=3,
        quote_count=4,
        view_count=5,
        bookmark_count=6,
        has_media=False,
        media_urls=[],
        url="https://x.com/trader/status/1790000000000000000",
    )


def test_tweets_command_reads_fetch_result(capsys) -> None:
    source = Mock()
    source.fetch_tweets.return_value = FetchResult(
        tweets=[_tweet()],
        reached_floor=True,
    )
    args = Namespace(
        provider="getxapi",
        handle="trader",
        start="2026-07-01",
        end="2026-07-01",
    )

    with patch("tweet_sources.factory.get_source", return_value=source):
        cmd_tweets(args)

    source.fetch_tweets.assert_called_once_with(
        "trader",
        datetime.date(2026, 7, 1),
        datetime.date(2026, 7, 1),
    )
    output = capsys.readouterr().out
    assert "Fetched 1 tweets for @trader" in output
    assert "1790000000000000000" in output
