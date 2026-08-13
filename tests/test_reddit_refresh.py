"""Tests for the Reddit-only refresh entrypoint (mocked pull, no network)."""
from pathlib import Path
from unittest.mock import patch

from casino_dashboard.jobs import reddit_refresh as rr


def test_resolve_tickers_from_argv():
    assert rr._resolve_tickers(["rklb", "asts"]) == ["RKLB", "ASTS"]


def test_resolve_tickers_defaults_to_universe():
    with patch("casino_dashboard.universe.load_universe") as mock_uni:
        mock_uni.return_value.all_tickers.return_value = {"BBB", "AAA"}
        assert rr._resolve_tickers([]) == ["AAA", "BBB"]  # sorted


def test_run_loads_map_and_delegates(tmp_path: Path):
    db = tmp_path / "t.db"
    with patch.object(rr, "load_subreddit_map", return_value={"RKLB": ["RocketLab"]}) as m, \
         patch.object(rr, "pull_reddit_for_tickers", return_value=(7, 2)) as pull:
        total, covered = rr.run(["RKLB", "ASTS"], db_path=db)

    assert (total, covered) == (7, 2)
    m.assert_called_once()
    # the loaded map is threaded through to the puller
    _, kwargs = pull.call_args
    assert kwargs["subreddit_map"] == {"RKLB": ["RocketLab"]}
