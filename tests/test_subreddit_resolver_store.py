"""Tests for the subreddit map store (config/ticker_subreddits.yaml)."""
from pathlib import Path

from core.social_media.reddit.resolver.store import (
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


# --- provenance, the general list, add/remove --------------------------------

import pytest  # noqa: E402

from core.social_media.reddit.resolver.store import (  # noqa: E402
    SubredditEntry,
    add_entries,
    clean_subreddit_name,
    load_entries,
    load_general_subreddits,
    remove_entry,
)


@pytest.mark.parametrize("raw,name", [
    ("wallstreetbets", "wallstreetbets"),
    ("  r/RKLB ", "RKLB"),
    ("/r/ASTSpaceMobile", "ASTSpaceMobile"),
    ("https://www.reddit.com/r/NBIS_Stock/", "NBIS_Stock"),
    ("old.reddit.com/r/stocks/comments/abc", "stocks"),
])
def test_clean_subreddit_name(raw, name):
    assert clean_subreddit_name(raw) == name


@pytest.mark.parametrize("raw", ["", "r/", "has space", "way_too_long_for_reddit_names", "bad-dash", "_lead"])
def test_clean_subreddit_name_rejects(raw):
    with pytest.raises(ValueError):
        clean_subreddit_name(raw)


def test_add_entries_appends_and_keeps_existing(tmp_path: Path):
    p = tmp_path / "map.yaml"
    save_subreddit_map({"RKLB": ["RocketLab"]}, updated="2026-08-13", path=p)
    added = add_entries([SubredditEntry(name="RKLB", ticker="rklb", source="manual", added="2026-09-27")], p)
    assert [e.ticker for e in added] == ["RKLB"]
    assert load_subreddit_map(p) == {"RKLB": ["RocketLab", "RKLB"]}


def test_add_entries_skips_duplicates_case_insensitively(tmp_path: Path):
    p = tmp_path / "map.yaml"
    add_entries([SubredditEntry(name="RocketLab", ticker="RKLB")], p)
    assert add_entries([SubredditEntry(name="rocketlab", ticker="RKLB")], p) == []
    assert load_subreddit_map(p) == {"RKLB": ["RocketLab"]}


def test_general_list_is_kept_apart_from_tickers(tmp_path: Path):
    p = tmp_path / "map.yaml"
    add_entries([SubredditEntry(name="wallstreetbets", source="manual", added="2026-09-27"),
                 SubredditEntry(name="RocketLab", ticker="RKLB")], p)
    assert load_subreddit_map(p) == {"RKLB": ["RocketLab"]}
    assert load_general_subreddits(p) == ["wallstreetbets"]


def test_load_entries_carries_details_and_legacy(tmp_path: Path):
    p = tmp_path / "map.yaml"
    save_subreddit_map({"RKLB": ["RocketLab"]}, updated="2026-08-13", path=p)   # legacy, no details
    add_entries([
        SubredditEntry(name="RKLB", ticker="RKLB", source="resolved", added="2026-09-27",
                       subscribers=1200, note="name + description match"),
        SubredditEntry(name="stocks", source="manual", added="2026-09-27"),
    ], p)
    by_name = {e.name: e for e in load_entries(p)}
    assert by_name["RocketLab"].source is None and by_name["RocketLab"].ticker == "RKLB"
    assert by_name["RKLB"].source == "resolved" and by_name["RKLB"].subscribers == 1200
    assert by_name["RKLB"].note == "name + description match"
    assert by_name["stocks"].ticker is None and by_name["stocks"].source == "manual"


def test_remove_entry(tmp_path: Path):
    p = tmp_path / "map.yaml"
    add_entries([SubredditEntry(name="RocketLab", ticker="RKLB", source="manual"),
                 SubredditEntry(name="RKLB", ticker="RKLB"),
                 SubredditEntry(name="stocks")], p)
    assert remove_entry("rocketlab", "RKLB", p) is True
    assert remove_entry("RocketLab", "RKLB", p) is False
    assert load_subreddit_map(p) == {"RKLB": ["RKLB"]}
    assert "RocketLab" not in {e.name for e in load_entries(p)}
    assert remove_entry("stocks", None, p) is True
    assert load_general_subreddits(p) == []


def test_removing_last_subreddit_drops_the_ticker(tmp_path: Path):
    p = tmp_path / "map.yaml"
    add_entries([SubredditEntry(name="RKLB", ticker="RKLB")], p)
    remove_entry("RKLB", "RKLB", p)
    assert load_subreddit_map(p) == {}


def test_rerunning_discovery_keeps_manual_entries(tmp_path: Path):
    p = tmp_path / "map.yaml"
    save_subreddit_map({"RKLB": ["OldAuto"]}, updated="2026-08-13", path=p)
    add_entries([SubredditEntry(name="MyPick", ticker="RKLB", source="manual", added="2026-09-27")], p)
    save_subreddit_map({"RKLB": ["RocketLab"]}, updated="2026-09-28", path=p)
    assert load_subreddit_map(p) == {"RKLB": ["RocketLab", "MyPick"]}
    manual = next(e for e in load_entries(p) if e.name == "MyPick")
    assert manual.source == "manual" and manual.added == "2026-09-27"


def test_hand_written_general_list_form_is_read(tmp_path: Path):
    p = tmp_path / "map.yaml"
    p.write_text("tickers: {}\ngeneral: [wallstreetbets, stocks]\n")
    assert load_general_subreddits(p) == ["wallstreetbets", "stocks"]
    add_entries([SubredditEntry(name="options")], p)
    assert load_general_subreddits(p) == ["wallstreetbets", "stocks", "options"]
