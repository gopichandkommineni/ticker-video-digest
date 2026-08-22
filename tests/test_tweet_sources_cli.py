"""The `python -m fintwit.tweet_sources` CLI, offline.

Regression cover for issue #121: `cmd_tweets` treated the adapter's return
value as a list, but adapters return a `FetchResult` whose tweets are one field
of it. `len()` on that raises TypeError, so the command died the moment a fetch
actually succeeded — which no test noticed, because nothing exercised the
success path without a network call.

Every test here mocks the adapter. Nothing reaches a provider and no API key is
needed.
"""
from __future__ import annotations

import argparse
from typing import Any
from unittest.mock import patch

import pytest

from fintwit.tweet_sources import __main__ as cli
from fintwit.tweet_sources.base import FetchResult, Tweet


def make_tweet(tweet_id: str = "1", text: str = "hello", **overrides: Any) -> Tweet:
    """A minimal valid Tweet. Only the fields the CLI prints matter here."""
    fields = dict(
        id=tweet_id,
        created_at_utc="2026-07-01T12:00:00Z",
        text=text,
        type="original",
        is_reply=False,
        is_quote=False,
        in_reply_to_id=None,
        quoted_tweet_id=None,
        quoted_author_id=None,
        conversation_id=None,
        like_count=1,
        retweet_count=0,
        reply_count=0,
        quote_count=0,
        view_count=10,
        bookmark_count=0,
        has_media=False,
        media_urls=[],
        url=f"https://x.com/someone/status/{tweet_id}",
    )
    fields.update(overrides)
    return Tweet(**fields)


class FakeSource:
    """Stands in for a provider adapter. Records the window it was asked for."""

    def __init__(self, result: FetchResult) -> None:
        self.result = result
        self.calls: list[tuple] = []

    def fetch_tweets(self, handle, start, end) -> FetchResult:
        self.calls.append((handle, start, end))
        return self.result


def run_cmd_tweets(result: FetchResult, handle: str = "someone") -> tuple[str, FakeSource]:
    """Run the tweets subcommand against a mocked adapter; return its stdout."""
    source = FakeSource(result)
    args = argparse.Namespace(
        provider="getxapi", handle=handle, start="2026-07-01", end="2026-07-02"
    )
    with patch("fintwit.tweet_sources.factory.get_source", return_value=source):
        import io
        import contextlib

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            cli.cmd_tweets(args)
        return buffer.getvalue(), source


def test_successful_fetch_prints_count_and_rows() -> None:
    """The exact path that raised TypeError in #121."""
    out, _ = run_cmd_tweets(
        FetchResult(
            tweets=[make_tweet("1", "first"), make_tweet("2", "second")],
            reached_floor=True,
        )
    )
    assert "Fetched 2 tweets for @someone" in out
    assert "first" in out and "second" in out
    assert "2026-07-01T12:00:00Z" in out


def test_empty_result_reports_zero_rather_than_crashing() -> None:
    out, _ = run_cmd_tweets(FetchResult(tweets=[], reached_floor=True))
    assert "Fetched 0 tweets for @someone" in out


def test_adapter_is_asked_for_the_parsed_date_window() -> None:
    import datetime

    _, source = run_cmd_tweets(FetchResult(tweets=[], reached_floor=True))
    handle, start, end = source.calls[0]
    assert handle == "someone"
    assert start == datetime.date(2026, 7, 1)
    assert end == datetime.date(2026, 7, 2)


def test_incomplete_window_is_flagged() -> None:
    """reached_floor=False means the count is a floor. Say so."""
    out, _ = run_cmd_tweets(
        FetchResult(tweets=[make_tweet()], reached_floor=False)
    )
    assert "WARNING" in out
    assert "page cap" in out


def test_complete_window_is_not_flagged() -> None:
    out, _ = run_cmd_tweets(FetchResult(tweets=[make_tweet()], reached_floor=True))
    assert "WARNING" not in out


def test_dropped_tweets_are_reported() -> None:
    out, _ = run_cmd_tweets(
        FetchResult(tweets=[make_tweet()], reached_floor=True, skipped=3)
    )
    assert "3 tweet(s) dropped" in out


def test_tweet_with_no_text_does_not_crash() -> None:
    out, _ = run_cmd_tweets(
        FetchResult(tweets=[make_tweet(text=None)], reached_floor=True)
    )
    assert "Fetched 1 tweets" in out


@pytest.mark.parametrize("subcommand", ["user-info", "tweets", "compare"])
def test_argument_parser_accepts_each_subcommand(subcommand: str) -> None:
    """The CLI still exposes all three commands with the arguments documented."""
    argv = ["--provider", "getxapi", "--handle", "someone"]
    if subcommand in ("tweets", "compare"):
        argv += ["--start", "2026-07-01", "--end", "2026-07-02"]
    if subcommand == "compare":
        argv = ["--handle", "someone", "--start", "2026-07-01", "--end", "2026-07-02"]

    with patch("sys.argv", ["tweet_sources", subcommand, *argv]), \
         patch.object(cli, "cmd_user_info"), \
         patch.object(cli, "cmd_tweets"), \
         patch.object(cli, "cmd_compare"):
        cli.main()  # raises SystemExit(2) if the parser rejects the arguments
