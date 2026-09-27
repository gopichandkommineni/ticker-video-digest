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
    assert cli.main(["add", "r/wallstreetbets", "--general"]) == 0
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


# --- input 2, automatic: which stock does this subreddit belong to? -----------------

from core.social_media.reddit.resolver import add_subreddit_auto, attribute_subreddit  # noqa: E402
from core.social_media.reddit.subreddit_catalog import UniverseEntry  # noqa: E402

_RAW = "core.social_media.reddit.arctic_shift_client.search_subreddits_raw"
_UNIVERSE_ENTRIES = [
    UniverseEntry(ticker="RKLB", company_name="Rocket Lab Corporation"),
    UniverseEntry(ticker="ASTS", company_name="AST SpaceMobile, Inc."),
    UniverseEntry(ticker="PATH", company_name="UiPath, Inc."),
]
_ARCHIVE = {
    "rocketlab": {"display_name": "RocketLab", "subscribers": 29000, "title": "Rocket Lab",
                  "public_description": "Unofficial community for Rocket Lab (RKLB)"},
    "wallstreetbets": {"display_name": "wallstreetbets", "subscribers": 15_000_000,
                       "title": "wallstreetbets", "public_description": "Like 4chan found a Bloomberg terminal"},
    "space": {"display_name": "space", "subscribers": 26_000_000, "title": "space",
              "public_description": "Share and discuss space news"},
    "uipathbulls": {"display_name": "UiPathBulls", "subscribers": 900, "title": "UiPath investors",
                    "public_description": "Discussion of UiPath stock, $PATH"},
}


def _archive(**kw):
    item = _ARCHIVE.get(kw["subreddit"].lower())
    return 200, [item] if item else []


@pytest.mark.parametrize("name,ticker", [
    ("RocketLab", "RKLB"),
    ("rocketlab", "RKLB"),
    ("https://reddit.com/r/UiPathBulls/", "PATH"),
    ("r/wallstreetbets", None),
    ("space", None),
])
def test_attribute_subreddit_from_archive(name, ticker):
    with patch(_RAW, side_effect=_archive):
        a = attribute_subreddit(name, _UNIVERSE_ENTRIES)
    assert a.ticker == ticker and a.found and a.archive_ok
    assert ("match" in a.reason) and (ticker or "any single stock") in a.reason


def test_attribute_uses_archive_spelling():
    with patch(_RAW, side_effect=_archive):
        a = attribute_subreddit("rocketlab", _UNIVERSE_ENTRIES)
    assert a.name == "RocketLab" and a.subscribers == 29000


def test_attribute_unknown_subreddit_judged_on_name():
    with patch(_RAW, side_effect=_archive):
        good = attribute_subreddit("RKLB_stock", _UNIVERSE_ENTRIES)
        vague = attribute_subreddit("SpaceStonks", _UNIVERSE_ENTRIES)
    assert good.ticker == "RKLB" and not good.found and good.archive_ok
    assert "doesn't know this subreddit" in good.reason
    assert vague.ticker is None


@pytest.mark.parametrize("failure", [lambda **kw: (0, []), lambda **kw: (503, [])])
def test_attribute_archive_down_falls_back_to_name(failure):
    with patch(_RAW, side_effect=failure):
        a = attribute_subreddit("ASTSpaceMobile", _UNIVERSE_ENTRIES)
    assert a.ticker == "ASTS" and not a.archive_ok and "couldn't be reached" in a.reason


def test_attribute_survives_transport_exception():
    with patch(_RAW, side_effect=ConnectionError("blocked")):
        a = attribute_subreddit("wallstreetbets", _UNIVERSE_ENTRIES)
    assert a.ticker is None and not a.archive_ok


def test_attribute_tie_goes_to_general():
    # Two share classes of one company: r/Alphabet fits both equally. A tie is
    # filed on the general list rather than guessed.
    tie = [UniverseEntry(ticker="GOOG", company_name="Alphabet Inc."),
           UniverseEntry(ticker="GOOGL", company_name="Alphabet Inc.")]
    with patch(_RAW, side_effect=lambda **kw: (200, [])):
        assert attribute_subreddit("Alphabet", tie).ticker is None
        assert attribute_subreddit("Alphabet", tie[:1]).ticker == "GOOG"


def test_add_subreddit_auto_files_under_stock_or_general(tmp_path: Path):
    p = tmp_path / "map.yaml"
    with patch(_RAW, side_effect=_archive):
        e1, a1 = add_subreddit_auto("RocketLab", _UNIVERSE_ENTRIES, path=p, added="2026-09-27")
        e2, _ = add_subreddit_auto("wallstreetbets", _UNIVERSE_ENTRIES, path=p)
        e3, a3 = add_subreddit_auto("rocketlab", _UNIVERSE_ENTRIES, path=p)
    assert e1.ticker == "RKLB" and e2.ticker is None
    assert e3 is None and a3.ticker == "RKLB"            # already there
    assert load_subreddit_map(p) == {"RKLB": ["RocketLab"]}
    assert load_general_subreddits(p) == ["wallstreetbets"]
    saved = next(e for e in load_entries(p) if e.name == "RocketLab")
    assert saved.source == "manual" and saved.subscribers == 29000
    assert "RKLB" in saved.note


def test_cli_add_auto(in_tmp, capsys):
    with patch(_RAW, side_effect=_archive), \
         patch.object(cli, "_universe_entries", return_value=_UNIVERSE_ENTRIES):
        assert cli.main(["add", "RocketLab"]) == 0
        assert cli.main(["add", "space"]) == 0
    out = capsys.readouterr().out
    assert "Added r/RocketLab to RKLB" in out and "Added r/space to the general list" in out
    assert "Why: Name and description match RKLB" in out
    assert load_subreddit_map(in_tmp) == {"RKLB": ["RocketLab"]}


def test_cli_add_with_ticker_or_general_skips_lookup(in_tmp):
    with patch(_RAW) as lookup:
        assert cli.main(["add", "SomeSub", "--ticker", "RKLB"]) == 0
        assert cli.main(["add", "OtherSub", "--general"]) == 0
    lookup.assert_not_called()
    assert load_subreddit_map(in_tmp) == {"RKLB": ["SomeSub"]}
    assert load_general_subreddits(in_tmp) == ["OtherSub"]


def test_cli_ticker_and_general_are_exclusive():
    with pytest.raises(SystemExit):
        cli._parse_args(["add", "x_sub", "--ticker", "RKLB", "--general"])


def test_page_auto_detects_stock(in_tmp):
    with patch("casino_dashboard.ui.loaders.load_universe_for_ui", return_value=_UNIVERSE), \
         patch("casino_dashboard.jobs.subreddit_catalog_run.load_company_names",
               return_value={"RKLB": "Rocket Lab Corporation"}), \
         patch(_RAW, side_effect=_archive):
        at = _app().run()
        next(t for t in at.text_input if t.label == "Subreddit").input("RocketLab")
        next(b for b in at.button if b.label == "Add subreddit").click()
        at.run()
        assert not at.exception
        assert any("Added r/RocketLab to RKLB" in s.value for s in at.success)
        next(t for t in at.text_input if t.label == "Subreddit").input("wallstreetbets")
        next(b for b in at.button if b.label == "Add subreddit").click()
        at.run()
    assert not at.exception
    assert any("Added r/wallstreetbets to the general list" in s.value for s in at.success)
    assert load_subreddit_map(in_tmp) == {"RKLB": ["RocketLab"]}
    assert load_general_subreddits(in_tmp) == ["wallstreetbets"]
