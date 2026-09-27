"""Tests for the subreddit resolver's two inputs, its CLI and its page (no network)."""
from pathlib import Path
from unittest.mock import patch

import pytest

from core.social_media.reddit.resolver import (
    add_subreddit,
    load_entries,
    load_general_subreddits,
    load_subreddit_map,
    resolve_company,
    save_resolved,
)
from core.social_media.reddit.subreddit_match import MatchCandidate, MatchResult, SubredditMetrics
from casino_dashboard.jobs import subreddit_resolve as cli

_RES = "core.social_media.reddit.resolver.resolve"


def _cand(name, subs, selected, reasons=("name + description match",)):
    return MatchCandidate(metrics=SubredditMetrics(name=name, subscribers=subs, measured=True),
                          relevance=0.9, selected=selected, reasons=list(reasons))


def _result(ticker="RKLB"):
    return MatchResult(query="Rocket Lab", ticker=ticker, company_name="Rocket Lab",
                       candidates=[_cand("RocketLab", 29000, True),
                                   _cand("RKLB", 4000, True),
                                   _cand("rocketry", 90000, False, ("no ticker or company in description",))])


# --- input 1: company name ------------------------------------------------------

def test_resolve_company_resolves_name_then_matches():
    with patch(f"{_RES}.resolve_ticker", return_value="RKLB") as rt, \
         patch(f"{_RES}.company_name_for") as cn, \
         patch(f"{_RES}.match", return_value=_result()) as m:
        resolve_company("Rocket Lab", universe={"RKLB"})
    rt.assert_called_once_with("Rocket Lab", {"RKLB"})
    cn.assert_not_called()                       # the query already is the company name
    assert m.call_args.kwargs == {"ticker": "RKLB", "company_name": "Rocket Lab", "with_metrics": True}


def test_resolve_company_from_ticker_looks_up_name():
    with patch(f"{_RES}.resolve_ticker", return_value="RKLB"), \
         patch(f"{_RES}.company_name_for", return_value="Rocket Lab Corporation"), \
         patch(f"{_RES}.match", return_value=_result()) as m:
        resolve_company("rklb")
    assert m.call_args.kwargs["company_name"] == "Rocket Lab Corporation"


def test_resolve_company_ticker_override():
    with patch(f"{_RES}.resolve_ticker", return_value=None), \
         patch(f"{_RES}.company_name_for", return_value=None), \
         patch(f"{_RES}.match", return_value=_result()) as m:
        resolve_company("Obscure Co", ticker="obsc")
    assert m.call_args.kwargs["ticker"] == "OBSC"
    assert m.call_args.kwargs["company_name"] == "Obscure Co"


def test_resolve_company_rejects_blank():
    with pytest.raises(ValueError):
        resolve_company("   ")


def test_save_resolved_saves_only_picked_with_evidence(tmp_path: Path):
    p = tmp_path / "map.yaml"
    saved = save_resolved(_result(), ["rocketlab", "RKLB"], path=p, added="2026-09-27")
    assert [e.name for e in saved] == ["RocketLab", "RKLB"]
    assert load_subreddit_map(p) == {"RKLB": ["RocketLab", "RKLB"]}
    rl = next(e for e in load_entries(p) if e.name == "RocketLab")
    assert rl.source == "resolved" and rl.subscribers == 29000 and rl.added == "2026-09-27"
    assert save_resolved(_result(), ["RocketLab"], path=p) == []      # already there


def test_save_resolved_needs_a_ticker(tmp_path: Path):
    with pytest.raises(ValueError, match="ticker"):
        save_resolved(_result(ticker=None), ["RocketLab"], path=tmp_path / "m.yaml")
    saved = save_resolved(_result(ticker=None), ["RocketLab"], ticker="rklb", path=tmp_path / "m.yaml")
    assert saved[0].ticker == "RKLB"


def test_save_resolved_rejects_unknown_names(tmp_path: Path):
    with pytest.raises(ValueError, match="nosuchsub"):
        save_resolved(_result(), ["NoSuchSub"], path=tmp_path / "m.yaml")


# --- input 2: subreddit name -----------------------------------------------------

def test_add_subreddit_general_and_ticker(tmp_path: Path):
    p = tmp_path / "map.yaml"
    e = add_subreddit("r/wallstreetbets", path=p, added="2026-09-27")
    assert e.name == "wallstreetbets" and e.ticker is None and e.source == "manual"
    add_subreddit("https://reddit.com/r/RKLB/", ticker="rklb", path=p)
    assert load_general_subreddits(p) == ["wallstreetbets"]
    assert load_subreddit_map(p) == {"RKLB": ["RKLB"]}
    assert add_subreddit("WallStreetBets", path=p) is None          # already there


def test_add_subreddit_rejects_bad_names(tmp_path: Path):
    with pytest.raises(ValueError):
        add_subreddit("not a sub", path=tmp_path / "m.yaml")


# --- CLI -------------------------------------------------------------------------

@pytest.fixture
def in_tmp(tmp_path, monkeypatch):
    """Run from an empty directory so the CLI's config/ path is a scratch file."""
    monkeypatch.chdir(tmp_path)
    return tmp_path / "config" / "ticker_subreddits.yaml"


def test_cli_add_list_remove(in_tmp, capsys):
    assert cli.main(["add", "r/wallstreetbets"]) == 0
    assert cli.main(["add", "RKLB", "--ticker", "rklb"]) == 0
    assert cli.main(["add", "RKLB", "--ticker", "RKLB"]) == 0
    assert cli.main(["add", "bad name"]) == 1
    out = capsys.readouterr().out
    assert "Added r/wallstreetbets to the general list" in out
    assert "Already on RKLB" in out and "not a valid subreddit name" in out

    cli.main(["list"])
    listing = capsys.readouterr().out
    assert "| general | r/wallstreetbets | manual |" in listing
    assert "| RKLB | r/RKLB | manual |" in listing

    assert cli.main(["remove", "r/RKLB", "--ticker", "RKLB"]) == 0
    assert load_subreddit_map(in_tmp) == {}


def test_cli_company_prints_without_saving(in_tmp, capsys):
    with patch.object(cli, "resolve_company", return_value=_result()), \
         patch.object(cli, "_universe_tickers", return_value=None):
        assert cli.main(["company", "Rocket Lab"]) == 0
    assert "Nothing saved" in capsys.readouterr().out
    assert not in_tmp.exists()


def test_cli_company_save_takes_confident_matches(in_tmp):
    with patch.object(cli, "resolve_company", return_value=_result()), \
         patch.object(cli, "_universe_tickers", return_value=None):
        assert cli.main(["company", "Rocket Lab", "--save"]) == 0
    assert load_subreddit_map(in_tmp) == {"RKLB": ["RocketLab", "RKLB"]}


def test_cli_company_pick(in_tmp):
    with patch.object(cli, "resolve_company", return_value=_result()), \
         patch.object(cli, "_universe_tickers", return_value=None):
        assert cli.main(["company", "Rocket Lab", "--pick", "r/rocketry"]) == 0
    assert load_subreddit_map(in_tmp) == {"RKLB": ["rocketry"]}


# --- page ------------------------------------------------------------------------

_PAGE = str(Path(__file__).resolve().parents[1] / "pages" / "07_Subreddits.py")
_UNIVERSE = {"ticker_to_sectors": {"RKLB": ["space"], "ASTS": ["space"]}, "sectors": {}}


def _app():
    from streamlit.testing.v1 import AppTest

    return AppTest.from_file(_PAGE, default_timeout=30)


def test_page_adds_a_subreddit_directly(in_tmp):
    with patch("casino_dashboard.ui.loaders.load_universe_for_ui", return_value=_UNIVERSE):
        at = _app().run()
        assert not at.exception
        name_box = next(t for t in at.text_input if t.label == "Subreddit")
        name_box.input("r/RKLB")
        next(s for s in at.selectbox if s.label == "For stock").select("RKLB")
        next(b for b in at.button if b.label == "Add subreddit").click()
        at.run()
    assert not at.exception
    assert any("Added r/RKLB to RKLB" in s.value for s in at.success)
    assert load_subreddit_map(in_tmp) == {"RKLB": ["RKLB"]}


def test_page_resolves_then_saves_ticked(in_tmp):
    with patch("casino_dashboard.ui.loaders.load_universe_for_ui", return_value=_UNIVERSE), \
         patch("core.social_media.reddit.resolver.resolve_company", return_value=_result()):
        at = _app().run()
        next(t for t in at.text_input if t.label == "Company name or ticker").input("Rocket Lab")
        next(b for b in at.button if b.label == "Search").click()
        at.run()
        assert not at.exception
        next(b for b in at.button if b.label == "Save ticked subreddits").click()
        at.run()
    assert not at.exception
    assert load_subreddit_map(in_tmp) == {"RKLB": ["RocketLab", "RKLB"]}
