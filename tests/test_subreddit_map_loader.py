"""Tests for the per-ticker subreddit map loader/saver."""
from pathlib import Path

from casino_dashboard.data.subreddit_map_loader import (
    load_subreddit_map,
    save_subreddit_map,
)


def test_load_missing_returns_empty(tmp_path: Path):
    assert load_subreddit_map(tmp_path / "nope.yaml") == {}


def test_save_then_load_roundtrip(tmp_path: Path):
    p = tmp_path / "map.yaml"
    save_subreddit_map({"rklb": ["RocketLab", "RKLB"], "ASTS": ["ASTSpaceMobile"]},
                       updated="2026-08-13", path=p)
    loaded = load_subreddit_map(p)
    assert loaded == {"RKLB": ["RocketLab", "RKLB"], "ASTS": ["ASTSpaceMobile"]}


def test_save_merges_and_preserves_other_tickers(tmp_path: Path):
    p = tmp_path / "map.yaml"
    save_subreddit_map({"RKLB": ["RocketLab"]}, updated="2026-08-13", path=p)
    # Second run only touches ASTS; RKLB (incl. a hand-edit) must survive.
    save_subreddit_map({"ASTS": ["ASTSpaceMobile"]}, updated="2026-08-14", path=p)
    loaded = load_subreddit_map(p)
    assert loaded == {"RKLB": ["RocketLab"], "ASTS": ["ASTSpaceMobile"]}


def test_save_overwrites_same_ticker(tmp_path: Path):
    p = tmp_path / "map.yaml"
    save_subreddit_map({"RKLB": ["OldSub"]}, updated="2026-08-13", path=p)
    save_subreddit_map({"RKLB": ["RocketLab", "RKLB"]}, updated="2026-08-14", path=p)
    assert load_subreddit_map(p) == {"RKLB": ["RocketLab", "RKLB"]}


def test_load_dedupes_and_skips_bad_entries(tmp_path: Path):
    p = tmp_path / "map.yaml"
    p.write_text(
        "tickers:\n"
        "  RKLB:\n"
        "    subreddits: [RocketLab, RocketLab, RKLB]\n"   # dupe
        "  BAD:\n"
        "    subreddits: notalist\n"                        # malformed -> skipped
    )
    loaded = load_subreddit_map(p)
    assert loaded["RKLB"] == ["RocketLab", "RKLB"]
    assert "BAD" not in loaded


def test_empty_tickers_map(tmp_path: Path):
    p = tmp_path / "map.yaml"
    p.write_text("tickers: {}\n")
    assert load_subreddit_map(p) == {}
