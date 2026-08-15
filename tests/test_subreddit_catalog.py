"""Unit tests for the catalog-first subreddit sweep — no real network calls."""
import json
from unittest.mock import patch

from core.social_media.reddit import subreddit_catalog as sc
from core.social_media.reddit.subreddit_catalog import (
    UniverseEntry,
    attribute_ticker,
    build_report,
    classify_market,
    fetch_catalog,
    info_from_item,
)
from core.social_media.reddit.subreddit_discovery import SubredditInfo


def _info(name, subs=1000, title="", desc=""):
    return SubredditInfo(
        name=name, subscribers=subs, title=title, public_description=desc
    )


# Sweep timestamps must sit after Reddit's epoch or the cursor never advances —
# the same guard that stops a real sweep from replaying page 1 forever.
_T0 = sc._REDDIT_EPOCH + 1000


def _item(name, subs=1000, created=_T0, title="", desc=""):
    return {
        "display_name": name,
        "subscribers": subs,
        "created_utc": created,
        "title": title,
        "public_description": desc,
    }


# ---------------------------------------------------------------------------
# Stage 1 — enumeration
# ---------------------------------------------------------------------------

def test_info_from_item_maps_fields():
    info = info_from_item(_item("stocks", 5_000_000, title="Stocks", desc="Equities"))
    assert info is not None
    assert info.name == "stocks"
    assert info.subscribers == 5_000_000
    assert info.title == "Stocks"


def test_info_from_item_rejects_invalid_names():
    assert info_from_item({"display_name": "no spaces here", "subscribers": 10}) is None
    assert info_from_item({"subscribers": 10}) is None


def test_fetch_catalog_pages_until_exhausted_and_sorts_desc():
    pages = [
        (200, [_item("small", 1_200, created=_T0), _item("huge", 900_000, created=_T0 + 10)]),
        (200, [_item("mid", 40_000, created=_T0 + 20)]),
        (200, []),
    ]
    with patch.object(sc, "_page", side_effect=pages) as page:
        infos, strategy, requests_made, truncated = fetch_catalog(
            min_subscribers=1000, max_requests=10, sleep=False
        )

    assert [i.name for i in infos] == ["huge", "mid", "small"]   # subscribers desc
    assert strategy == "created+min_subscribers"
    assert requests_made == 3
    assert not truncated
    # The cursor advances to the newest creation time seen, so page 2 asks for
    # what came after page 1 rather than replaying it.
    assert page.call_args_list[1].kwargs["after"] == _T0 + 10


def test_fetch_catalog_applies_subscriber_floor_locally():
    with patch.object(sc, "_page", side_effect=[
        (200, [_item("tiny", 5, created=_T0), _item("big", 5_000, created=_T0 + 10)]),
        (200, []),
    ]):
        infos, _, _, _ = fetch_catalog(min_subscribers=1000, max_requests=10, sleep=False)
    assert [i.name for i in infos] == ["big"]


def test_fetch_catalog_stops_when_cursor_stalls():
    """Every item sharing one timestamp must not spin the same page forever."""
    with patch.object(sc, "_page", return_value=(200, [_item("aaa", 2000, created=_T0)])):
        infos, _, requests_made, _ = fetch_catalog(
            min_subscribers=1000, max_requests=50, sleep=False
        )
    assert requests_made == 2   # first page, then one more that made no progress
    assert [i.name for i in infos] == ["aaa"]


def test_fetch_catalog_marks_truncated_when_budget_runs_out():
    def endless(**kwargs):
        after = kwargs.get("after", _T0)
        return (200, [_item(f"s{after}", 2000, created=after + 100)])

    with patch.object(sc, "_page", side_effect=endless):
        _, _, requests_made, truncated = fetch_catalog(
            min_subscribers=1000, max_requests=4, sleep=False
        )
    assert requests_made == 4
    assert truncated


def test_fetch_catalog_drops_min_subscribers_when_rejected():
    """A 400 on page 1 means the param is unsupported — retry without it."""
    calls = []

    def responder(**kwargs):
        calls.append(kwargs)
        if "min_subscribers" in kwargs:
            return (400, [])
        if kwargs.get("after", 0) <= _T0:
            return (200, [_item("okay", 3000, created=_T0 + 10)])
        return (200, [])

    with patch.object(sc, "_page", side_effect=responder):
        infos, strategy, _, _ = fetch_catalog(
            min_subscribers=1000, max_requests=10, sleep=False
        )
    assert strategy == "created"
    assert [i.name for i in infos] == ["okay"]


def test_fetch_catalog_falls_back_to_backward_paging_when_sort_rejected():
    """An archive that rejects `sort` still gets swept — newest-first instead."""
    def responder(**kwargs):
        if "sort" in kwargs:
            return (400, [])
        if "before" in kwargs and kwargs["before"] > _T0:
            return (200, [_item("backward", 7_000, created=_T0)])
        return (200, [])

    with patch.object(sc, "_page", side_effect=responder):
        infos, strategy, _, _ = fetch_catalog(
            min_subscribers=1000, max_requests=20, sleep=False
        )
    assert strategy == "created-desc+min_subscribers"
    assert [i.name for i in infos] == ["backward"]


def test_fetch_catalog_stops_at_the_first_shape_that_returns_rows():
    with patch.object(sc, "_page", side_effect=[
        (200, [_item("first", 4_000, created=_T0)]),
        (200, []),
    ]) as page:
        _, strategy, _, _ = fetch_catalog(min_subscribers=1000, max_requests=20, sleep=False)
    assert strategy == "created+min_subscribers"
    assert page.call_count == 2      # no later shape was attempted


def test_fetch_catalog_falls_back_to_prefix_sweep():
    """When creation-time paging is unavailable entirely, sweep by prefix."""
    def responder(**kwargs):
        if "query" in kwargs:
            return (200, [_item(f"{kwargs['query']}sub", 2000)])
        return (400, [])

    with patch.object(sc, "_page", side_effect=responder):
        infos, strategy, _, _ = fetch_catalog(
            min_subscribers=1000, max_requests=50, sleep=False, prefixes=["a", "b"]
        )
    assert strategy == "prefix"
    assert sorted(i.name for i in infos) == ["asub", "bsub"]


# ---------------------------------------------------------------------------
# Stage 2 — market classification
# ---------------------------------------------------------------------------

def test_classify_market_strong_name_terms():
    for name in ("stocks", "StockMarket", "wallstreetbets", "pennystocks",
                 "CanadianInvestor", "ASX_Stocks", "Daytrading"):
        assert classify_market(_info(name)).is_market, name


def test_classify_market_rejects_lookalike_names():
    """Token matching, not substring — these must not read as stock subs."""
    for name in ("Stockholm", "marketing", "livestock", "supermarket",
                 "stockphotography", "AskReddit"):
        assert not classify_market(_info(name)).is_market, name


def test_classify_market_weak_name_needs_context():
    lonely = _info("TradingCardGames", title="Trade your cards", desc="Card swaps")
    assert not classify_market(lonely).is_market

    real = _info("Trading", title="Trading", desc="Discuss equities and earnings")
    verdict = classify_market(real)
    assert verdict.is_market
    assert verdict.rule == "name-weak+context"


def test_classify_market_text_route_for_neutral_names():
    """A company sub whose name says nothing still qualifies on its description."""
    verdict = classify_market(
        _info("ASTSpaceMobile", desc="For investors and shareholders discussing the stock")
    )
    assert verdict.is_market
    assert verdict.rule == "text"


def test_classify_market_text_route_needs_two_finance_words():
    assert not classify_market(_info("SomeHobby", desc="We share our portfolio of art")).is_market


def test_classify_market_ticker_attribution_qualifies():
    verdict = classify_market(
        _info("RocketLab"), ticker=sc.TickerMatch(ticker="RKLB", relevance=0.6)
    )
    assert verdict.is_market
    assert verdict.rule == "ticker"


# ---------------------------------------------------------------------------
# Stage 3 — per-stock attribution
# ---------------------------------------------------------------------------

_ENTRIES = [
    UniverseEntry(ticker="RKLB", company_name="Rocket Lab USA, Inc."),
    UniverseEntry(ticker="ASTS", company_name="AST SpaceMobile, Inc."),
    UniverseEntry(ticker="PL", company_name="Planet Labs PBC"),
]


def test_attribute_ticker_matches_symbol_and_company_names():
    assert attribute_ticker(_info("RKLB", 5_000), _ENTRIES).ticker == "RKLB"
    assert attribute_ticker(_info("RocketLab", 20_000), _ENTRIES).ticker == "RKLB"
    assert attribute_ticker(_info("ASTSpaceMobile", 90_000), _ENTRIES).ticker == "ASTS"


def test_attribute_ticker_ignores_unrelated_giants():
    assert attribute_ticker(_info("playstation", 8_000_000), _ENTRIES) is None
    assert attribute_ticker(_info("wallstreetbets", 15_000_000), _ENTRIES) is None


def test_attribute_ticker_respects_subscriber_floor():
    tiny = _info("RKLB", 10)
    assert attribute_ticker(tiny, _ENTRIES, min_subscribers=50) is None
    assert attribute_ticker(tiny, _ENTRIES, min_subscribers=0).ticker == "RKLB"


def test_attribute_ticker_leaves_ambiguous_subs_unattributed():
    """Two stocks matching equally well is a coin flip we refuse to make."""
    entries = [
        UniverseEntry(ticker="AAA", company_name="Nova Systems"),
        UniverseEntry(ticker="BBB", company_name="Nova Systems"),
    ]
    assert attribute_ticker(_info("NovaSystems", 5_000), entries) is None


# ---------------------------------------------------------------------------
# Orchestration + report
# ---------------------------------------------------------------------------

def _sample_report():
    infos = [
        _info("wallstreetbets", 15_000_000, title="wallstreetbets"),
        _info("Stockholm", 300_000, title="Stockholm, Sweden"),
        _info("RKLB", 30_000, title="Rocket Lab", desc="Stock discussion for investors"),
        _info("RocketLab", 12_000, title="Rocket Lab"),
    ]
    return build_report(_ENTRIES, infos=infos, ticker_min_subscribers=50)


def test_build_report_partitions_the_three_stages():
    report = _sample_report()
    assert [r.info.name for r in report.rows] == [
        "wallstreetbets", "Stockholm", "RKLB", "RocketLab"
    ]                                                    # subscribers desc
    assert {r.info.name for r in report.market_rows} == {
        "wallstreetbets", "RKLB", "RocketLab"
    }                                                    # Stockholm filtered out
    assert {r.info.name for r in report.ticker_rows} == {"RKLB", "RocketLab"}
    assert report.by_ticker() == {"RKLB": ["RKLB", "RocketLab"]}


def test_build_report_from_supplied_infos_makes_no_requests():
    with patch.object(sc, "_page", side_effect=AssertionError("network touched")):
        report = _sample_report()
    assert report.strategy == "supplied"
    assert report.requests_made == 0


def test_report_lines_render_all_stages_and_flag_missing_tickers():
    from casino_dashboard.jobs.subreddit_catalog_run import report_lines

    text = "\n".join(report_lines(_sample_report(), expected_tickers={"RKLB", "ASTS"}))
    assert "Stage 1" in text and "Stage 2" in text and "Stage 3" in text
    assert "r/RKLB" in text
    assert "**RKLB**" in text
    assert "No subreddit found for 1 ticker(s):** ASTS" in text


def test_report_lines_warn_on_truncated_and_fallback_sweeps():
    from casino_dashboard.jobs.subreddit_catalog_run import report_lines

    report = _sample_report()
    report.truncated = True
    report.strategy = "prefix"
    text = "\n".join(report_lines(report))
    assert "Incomplete sweep" in text
    assert "Fallback strategy" in text


def test_write_artifacts_dumps_csv_and_json(tmp_path):
    from casino_dashboard.jobs.subreddit_catalog_run import write_artifacts

    paths = write_artifacts(_sample_report(), tmp_path, "2026-08-15")
    csv_text = paths[0].read_text()
    assert "subreddit,subscribers" in csv_text
    assert "wallstreetbets" in csv_text

    payload = json.loads(paths[1].read_text())
    assert payload["tickers"] == {"RKLB": ["RKLB", "RocketLab"]}
    assert payload["strategy"] == "supplied"
