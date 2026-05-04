"""Tests for casino_dashboard.data.reddit_client — PRAW fully mocked."""
import re
from unittest.mock import MagicMock, patch

import pytest

from casino_dashboard.data.reddit_client import (
    AMBIGUOUS_TICKERS,
    SUBREDDITS,
    RedditMention,
    build_ticker_pattern,
    count_mentions_in_subreddit,
    fetch_reddit_mentions_for_universe,
    get_reddit_client,
)


# ---------------------------------------------------------------------------
# build_ticker_pattern
# ---------------------------------------------------------------------------

class TestBuildTickerPattern:
    def test_aaoi_matches_dollar_prefix(self):
        pat = build_ticker_pattern("AAOI")
        assert pat.search("I love $AAOI today")

    def test_aaoi_matches_bare_uppercase(self):
        pat = build_ticker_pattern("AAOI")
        assert pat.search("AAOI to the moon")

    def test_aaoi_matches_dollar_lowercase(self):
        pat = build_ticker_pattern("AAOI")
        assert pat.search("buying $aaoi now")

    def test_aaoi_does_not_match_inside_longer_token(self):
        pat = build_ticker_pattern("AAOI")
        assert not pat.search("AAOIX is a fake ticker")

    def test_ag_ambiguous_matches_dollar_prefix(self):
        pat = build_ticker_pattern("AG")
        assert pat.search("buying $AG silver")

    def test_ag_ambiguous_does_not_match_bare(self):
        pat = build_ticker_pattern("AG")
        assert not pat.search("AG industries looks good")

    def test_ag_ambiguous_does_not_match_again(self):
        pat = build_ticker_pattern("AG")
        assert not pat.search("AGAIN tomorrow we moon")

    def test_poet_ambiguous_requires_dollar(self):
        pat = build_ticker_pattern("POET")
        assert pat.search("$POET breakout incoming")

    def test_poet_ambiguous_does_not_match_poetry(self):
        pat = build_ticker_pattern("POET")
        assert not pat.search("POETRY is beautiful")

    def test_poet_ambiguous_does_not_match_bare(self):
        pat = build_ticker_pattern("POET")
        assert not pat.search("POET Technologies is legit")

    def test_case_insensitive_unambiguous(self):
        pat = build_ticker_pattern("RKLB")
        assert pat.search("rklb is pumping")  # bare lowercase should match

    def test_unambiguous_word_boundary_no_prefix_match(self):
        pat = build_ticker_pattern("MP")
        # MP is in AMBIGUOUS_TICKERS, so bare MP should not match
        assert not pat.search("MP Materials is interesting")


# ---------------------------------------------------------------------------
# get_reddit_client
# ---------------------------------------------------------------------------

class TestGetRedditClient:
    def test_missing_env_vars_returns_none(self, monkeypatch):
        monkeypatch.delenv("REDDIT_CLIENT_ID", raising=False)
        monkeypatch.delenv("REDDIT_CLIENT_SECRET", raising=False)
        monkeypatch.delenv("REDDIT_USER_AGENT", raising=False)
        result = get_reddit_client()
        assert result is None

    def test_partial_env_vars_returns_none(self, monkeypatch):
        monkeypatch.setenv("REDDIT_CLIENT_ID", "abc")
        monkeypatch.delenv("REDDIT_CLIENT_SECRET", raising=False)
        monkeypatch.delenv("REDDIT_USER_AGENT", raising=False)
        result = get_reddit_client()
        assert result is None

    def test_all_env_vars_present_returns_reddit_instance(self, monkeypatch):
        monkeypatch.setenv("REDDIT_CLIENT_ID", "test_id")
        monkeypatch.setenv("REDDIT_CLIENT_SECRET", "test_secret")
        monkeypatch.setenv("REDDIT_USER_AGENT", "test_agent/1.0")

        mock_reddit_instance = MagicMock()
        mock_reddit_class = MagicMock(return_value=mock_reddit_instance)

        with patch.dict("sys.modules", {"praw": MagicMock(Reddit=mock_reddit_class)}):
            result = get_reddit_client()

        assert result is mock_reddit_instance
        mock_reddit_class.assert_called_once_with(
            client_id="test_id",
            client_secret="test_secret",
            user_agent="test_agent/1.0",
            read_only=True,
        )


# ---------------------------------------------------------------------------
# count_mentions_in_subreddit
# ---------------------------------------------------------------------------

def _make_post(title: str, selftext: str = "", score: int = 10, comments: list = None):
    post = MagicMock()
    post.title = title
    post.selftext = selftext
    post.score = score
    post.id = "abc123"
    comment_forest = MagicMock()
    comment_forest.__iter__ = MagicMock(return_value=iter(comments or []))
    comment_forest.replace_more = MagicMock()
    post.comments = comment_forest
    return post


def _make_comment(body: str, score: int = 5):
    c = MagicMock()
    c.body = body
    c.score = score
    return c


class TestCountMentionsInSubreddit:
    def test_empty_results_returns_zero(self):
        reddit = MagicMock()
        reddit.subreddit.return_value.search.return_value = iter([])
        result = count_mentions_in_subreddit(reddit, "stocks", "AAOI")
        assert result.mention_count == 0
        assert result.upvote_sum == 0
        assert result.ticker == "AAOI"
        assert result.subreddit == "stocks"

    def test_three_matching_posts_returns_count_3(self):
        reddit = MagicMock()
        posts = [
            _make_post("$AAOI is up today", score=10),
            _make_post("I bought AAOI calls", score=20),
            _make_post("AAOI earnings next week", score=5),
        ]
        reddit.subreddit.return_value.search.return_value = iter(posts)
        result = count_mentions_in_subreddit(reddit, "wallstreetbets", "AAOI")
        assert result.mention_count == 3
        assert result.upvote_sum == 35

    def test_two_posts_plus_five_matching_comments_returns_7(self):
        comments = [_make_comment(f"$AAOI comment {i}", score=2) for i in range(5)]
        posts = [
            _make_post("$AAOI is pumping", score=10, comments=comments),
            _make_post("$AAOI to the moon", score=15, comments=[]),
        ]
        reddit = MagicMock()
        reddit.subreddit.return_value.search.return_value = iter(posts)
        result = count_mentions_in_subreddit(reddit, "stocks", "AAOI")
        # 2 posts + 5 comments = 7
        assert result.mention_count == 7

    def test_search_timeout_returns_zeros_gracefully(self):
        reddit = MagicMock()
        reddit.subreddit.return_value.search.side_effect = Exception("RequestException: timeout")
        result = count_mentions_in_subreddit(reddit, "options", "RKLB")
        assert result.mention_count == 0
        assert result.upvote_sum == 0
        assert result.ticker == "RKLB"

    def test_non_matching_posts_not_counted(self):
        posts = [
            _make_post("SPY puts for Monday", score=10),
            _make_post("TSLA calls EV play", score=20),
        ]
        reddit = MagicMock()
        reddit.subreddit.return_value.search.return_value = iter(posts)
        result = count_mentions_in_subreddit(reddit, "wallstreetbets", "AAOI")
        assert result.mention_count == 0


# ---------------------------------------------------------------------------
# fetch_reddit_mentions_for_universe
# ---------------------------------------------------------------------------

class TestFetchRedditMentionsForUniverse:
    def test_none_client_returns_empty_list(self):
        result = fetch_reddit_mentions_for_universe(None, ["AAOI", "RKLB", "IONQ"])
        assert result == []

    def test_three_tickers_two_subreddits_returns_six_results(self, monkeypatch):
        # Patch SUBREDDITS to 2 for this test
        monkeypatch.setattr(
            "casino_dashboard.data.reddit_client.SUBREDDITS",
            ["wallstreetbets", "stocks"],
        )
        reddit = MagicMock()
        reddit.subreddit.return_value.search.return_value = iter([])

        results = fetch_reddit_mentions_for_universe(reddit, ["AAOI", "RKLB", "IONQ"])
        assert len(results) == 6
        tickers_seen = {r.ticker for r in results}
        assert tickers_seen == {"AAOI", "RKLB", "IONQ"}

    def test_results_are_reddit_mention_instances(self, monkeypatch):
        monkeypatch.setattr(
            "casino_dashboard.data.reddit_client.SUBREDDITS",
            ["stocks"],
        )
        reddit = MagicMock()
        reddit.subreddit.return_value.search.return_value = iter([])
        results = fetch_reddit_mentions_for_universe(reddit, ["COIN"])
        assert len(results) == 1
        assert isinstance(results[0], RedditMention)
