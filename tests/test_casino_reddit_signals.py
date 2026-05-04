"""Tests for Reddit signals computed in signals/orchestrator.py."""
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

from casino_dashboard.signals.orchestrator import compute_reddit_signals_for_ticker


def _make_reddit_df(rows: list[dict]) -> pd.DataFrame:
    """Build a DataFrame matching the schema returned by get_reddit_mentions_for_ticker."""
    return pd.DataFrame(rows, columns=["date", "subreddit", "mention_count", "upvote_sum"])


class TestRedditMentionsToday:
    def test_aggregates_across_subreddits(self, tmp_path, monkeypatch):
        """reddit_mentions_today sums mention_count across all subreddits for today."""
        today = date.today().isoformat()
        rows = [
            {"date": today, "subreddit": "wallstreetbets", "mention_count": 10, "upvote_sum": 50},
            {"date": today, "subreddit": "stocks", "mention_count": 5, "upvote_sum": 20},
            {"date": today, "subreddit": "options", "mention_count": 3, "upvote_sum": 10},
        ]
        df = _make_reddit_df(rows)

        import casino_dashboard.signals.orchestrator as orch
        monkeypatch.setattr(orch, "get_reddit_mentions_for_ticker", lambda ticker, days, db_path: df)

        signals = compute_reddit_signals_for_ticker("AAOI", tmp_path / "test.db")
        assert "reddit_mentions_today" in signals
        assert signals["reddit_mentions_today"] == 18.0


class TestRedditVelocity7d:
    def test_8_days_returns_expected_ratio(self, tmp_path, monkeypatch):
        """With 8 days of data, velocity = today / mean(prior 7 days)."""
        today = date.today()
        rows = []
        # Today: 80 mentions, prior 7 days: 10 each → velocity = 80/10 = 8.0
        for i in range(8):
            d = (today - timedelta(days=i)).isoformat()
            count = 80 if i == 0 else 10
            rows.append({"date": d, "subreddit": "stocks", "mention_count": count, "upvote_sum": 0})

        df = _make_reddit_df(rows)

        import casino_dashboard.signals.orchestrator as orch
        monkeypatch.setattr(orch, "get_reddit_mentions_for_ticker", lambda ticker, days, db_path: df)

        signals = compute_reddit_signals_for_ticker("RKLB", tmp_path / "test.db")
        assert "reddit_velocity_7d" in signals
        assert abs(signals["reddit_velocity_7d"] - 8.0) < 0.01

    def test_fewer_than_8_days_returns_no_velocity(self, tmp_path, monkeypatch):
        """With fewer than 8 distinct days, reddit_velocity_7d is not computed."""
        today = date.today()
        rows = []
        for i in range(5):  # only 5 days
            d = (today - timedelta(days=i)).isoformat()
            rows.append({"date": d, "subreddit": "stocks", "mention_count": 10, "upvote_sum": 0})

        df = _make_reddit_df(rows)

        import casino_dashboard.signals.orchestrator as orch
        monkeypatch.setattr(orch, "get_reddit_mentions_for_ticker", lambda ticker, days, db_path: df)

        signals = compute_reddit_signals_for_ticker("IONQ", tmp_path / "test.db")
        assert "reddit_velocity_7d" not in signals

    def test_no_reddit_data_signals_omitted(self, tmp_path, monkeypatch):
        """When no Reddit rows exist, neither signal is present (not None)."""
        empty_df = _make_reddit_df([])

        import casino_dashboard.signals.orchestrator as orch
        monkeypatch.setattr(orch, "get_reddit_mentions_for_ticker", lambda ticker, days, db_path: empty_df)

        signals = compute_reddit_signals_for_ticker("COIN", tmp_path / "test.db")
        assert "reddit_mentions_today" not in signals
        assert "reddit_velocity_7d" not in signals
