"""Unit tests for the read-only subreddit discovery runner (mocked discover)."""
from unittest.mock import patch

from core.social_media.reddit.subreddit_discovery import (
    DiscoveryResult,
    ScoredSubreddit,
    SubredditInfo,
)
from casino_dashboard.jobs import subreddit_discovery_run as runner


def _scored(name, subs, selected):
    return ScoredSubreddit(
        info=SubredditInfo(name=name, subscribers=subs, active_online=5, posts_7d=10),
        relevance=1.0, score=99.0, selected=selected,
        reasons=["selected"] if selected else ["only 3 subscribers"],
    )


def test_resolve_queries_precedence(monkeypatch):
    assert runner._resolve_queries(["RKLB", "Rocket Lab"]) == ["RKLB", "Rocket Lab"]
    monkeypatch.setenv("SUBREDDIT_DISCOVERY_QUERIES", "AAA, BBB")
    assert runner._resolve_queries([]) == ["AAA", "BBB"]
    monkeypatch.delenv("SUBREDDIT_DISCOVERY_QUERIES")
    assert runner._resolve_queries([]) == runner._DEFAULT_QUERIES


def test_run_renders_selected_and_flag():
    result = DiscoveryResult(
        ticker="RKLB", company_name="Rocket Lab",
        candidates_checked=12,
        subreddits=[_scored("RocketLab", 42000, True), _scored("RKLBfan", 3, False)],
        flag=None,
    )
    with patch.object(runner, "resolve_ticker", return_value="RKLB"), \
         patch.object(runner, "company_name_for", return_value="Rocket Lab"), \
         patch.object(runner, "_universe_tickers", return_value=None), \
         patch.object(runner, "discover", return_value=result):
        lines = runner.run(["RKLB"], sleep=False)

    text = "\n".join(lines)
    assert "RKLB — Rocket Lab" in text
    assert "r/RocketLab" in text
    assert "✅ selected" in text
    assert "✖" in text  # the noise sub


def test_run_flags_unresolved_query():
    with patch.object(runner, "resolve_ticker", return_value=None), \
         patch.object(runner, "_universe_tickers", return_value=None):
        lines = runner.run(["Totally Fake Co"], sleep=False)
    assert any("could not resolve" in ln for ln in lines)


def test_run_flags_nothing_found():
    result = DiscoveryResult(ticker="ZZZZ", candidates_checked=8, subreddits=[], flag=None)
    with patch.object(runner, "resolve_ticker", return_value="ZZZZ"), \
         patch.object(runner, "company_name_for", return_value=None), \
         patch.object(runner, "_universe_tickers", return_value=None), \
         patch.object(runner, "discover", return_value=result):
        lines = runner.run(["ZZZZ"], sleep=False)
    assert any("No matching subreddit found" in ln for ln in lines)


def test_run_save_persists_selected_subreddits():
    result = DiscoveryResult(
        ticker="RKLB", company_name="Rocket Lab",
        subreddits=[_scored("RocketLab", 42000, True), _scored("RKLBfan", 3, False)],
    )
    with patch.object(runner, "resolve_ticker", return_value="RKLB"), \
         patch.object(runner, "company_name_for", return_value="Rocket Lab"), \
         patch.object(runner, "_universe_tickers", return_value=None), \
         patch.object(runner, "discover", return_value=result), \
         patch.object(runner, "save_subreddit_map") as mock_save:
        runner.run(["RKLB"], sleep=False, save=True)

    # Only the SELECTED subreddit is persisted (noise dropped).
    args, kwargs = mock_save.call_args
    assert args[0] == {"RKLB": ["RocketLab"]}
