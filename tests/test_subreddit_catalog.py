"""Unit tests for the catalog-first subreddit sweep — no real network calls."""
import json
from unittest.mock import patch

import pytest

from core.social_media.reddit import arctic_shift_client as arctic
from core.social_media.reddit import subreddit_catalog as sc
from core.social_media.reddit.subreddit_catalog import (
    UniverseEntry,
    attribute_ticker,
    build_report,
    classify_market,
    fetch_catalog,
    info_from_item,
)
from core.social_media.reddit.subreddit_discovery import ScoredSubreddit, SubredditInfo


def _info(name, subs=1000, title="", desc=""):
    return SubredditInfo(
        name=name, subscribers=subs, title=title, public_description=desc
    )


# Captured before the autouse fixture replaces it, so the test that exercises the
# ranked sweep itself can still reach the real implementation.
_REAL_RANKED_SWEEP = sc._sweep_by_subscribers


@pytest.fixture(autouse=True)
def _isolate_the_company_name_cache(tmp_path, monkeypatch):
    """No test may write the real config/ticker_company_names.yaml.

    An earlier version of this suite did exactly that — the cache path was a
    default argument bound at import time, so a test's fake resolver wrote
    "RKLB Corp" into the committed cache. Cached names are believed over
    yfinance, so that quietly cost RKLB and ASTS their real company names and
    with them every company-named match (r/RocketLab, r/ASTSpaceMobile).
    """
    from casino_dashboard.jobs import subreddit_catalog_run as job  # noqa: PLC0415

    monkeypatch.setattr(job, "_NAMES_CACHE", tmp_path / "ticker_company_names.yaml")


@pytest.fixture(autouse=True)
def _archive_without_subscriber_ranking():
    """Default every test to an archive that cannot rank by subscribers.

    Stage 1 tries the ranked walk first, and it talks to the network through a
    different door than `_page` — so without this the creation-time tests would
    reach for the real archive. Tests covering the ranked path re-patch this.
    """
    with patch.object(
        sc, "_sweep_by_subscribers",
        side_effect=arctic.SubscriberSortUnsupported("ranking unavailable"),
    ):
        yield


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


def test_fetch_catalog_prefers_the_archives_own_subscriber_ranking():
    """The ranked walk is the point — creation-time paging is only a fallback."""
    ranked = {
        "huge": _info("huge", 900_000),
        "mid": _info("mid", 40_000),
    }
    with patch.object(sc, "_sweep_by_subscribers", return_value=(ranked, 1, False)) as ranked_sweep, \
         patch.object(sc, "_page", side_effect=AssertionError("fell back needlessly")):
        infos, strategy, requests_made, truncated = fetch_catalog(
            min_subscribers=1000, max_requests=600, sleep=False
        )
    assert strategy == "subscribers"
    assert [i.name for i in infos] == ["huge", "mid"]
    assert requests_made == 1
    assert not truncated
    assert ranked_sweep.call_args.args[0] == 1000      # floor passed through


def test_sweep_by_subscribers_maps_items_and_applies_the_floor():
    items = [
        {"display_name": "big", "subscribers": 500_000},
        {"display_name": "tiny", "subscribers": 12},        # below the floor
        {"display_name": "no spaces allowed", "subscribers": 90_000},   # invalid name
    ]
    with patch.object(arctic, "iter_subreddits_by_subscribers", return_value=iter(items)):
        found, _, truncated = _REAL_RANKED_SWEEP(1000, max_requests=10, sleep=False)
    assert list(found) == ["big"]
    assert not truncated


def test_ranked_sweep_honours_the_request_budget():
    """--max-requests must bound the ranked walk too, in pages like every other."""
    captured = {}

    def fake_iter(min_subscribers, max_count, page_size, sleep):
        captured["max_count"] = max_count
        return iter([{"display_name": f"s{i:05d}", "subscribers": 5_000}
                     for i in range(max_count)])

    with patch.object(arctic, "iter_subreddits_by_subscribers", side_effect=fake_iter):
        found, requests_made, truncated = _REAL_RANKED_SWEEP(
            1000, max_requests=3, sleep=False
        )
    assert captured["max_count"] == 3 * sc._RANKED_PAGE_SIZE   # 3 pages, not unbounded
    assert len(found) == 3 * sc._RANKED_PAGE_SIZE
    assert requests_made == 3
    assert truncated          # budget stopped it, so the catalog is a lower bound


def test_fetch_catalog_falls_back_when_ranking_is_rejected():
    """A rejected ranked query must degrade, not report an empty Reddit."""
    with patch.object(sc, "_page", side_effect=[
        (200, [_item("viacreated", 5_000, created=_T0)]),
        (200, []),
    ]):
        infos, strategy, _, _ = fetch_catalog(
            min_subscribers=1000, max_requests=20, sleep=False
        )
    assert strategy == "created+min_subscribers"        # the autouse fixture rejected ranking
    assert [i.name for i in infos] == ["viacreated"]


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


def test_newest_first_sweeps_backwards_from_today():
    """A partial budget should land on recent subs, where ticker communities are."""
    with patch.object(sc, "_page", side_effect=[
        (200, [_item("recent", 3_000, created=_T0 + 500)]),
        (200, []),
    ]) as page:
        _, strategy, _, _ = fetch_catalog(
            min_subscribers=1000, max_requests=10, sleep=False, newest_first=True
        )
    assert strategy == "created-desc+min_subscribers"
    assert "before" in page.call_args_list[0].kwargs
    assert "after" not in page.call_args_list[0].kwargs


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


def test_prefix_sweep_deepens_only_into_full_pages():
    """A full page means more is hiding behind that prefix; a short one is done."""
    def responder(**kwargs):
        prefix = kwargs["query"]
        if prefix == "a":                     # full -> expand into a?, a?, …
            return (200, [_item(f"a{i:03d}xx", 2000) for i in range(sc._PAGE_SIZE)])
        if prefix == "b":                     # short -> exhausted, no children
            return (200, [_item("bsub", 2000)])
        return (200, [])

    with patch.object(sc, "_page", side_effect=responder) as page:
        found, _, truncated = sc._sweep_by_prefix(
            1000, max_requests=200, prefixes=["a", "b"], sleep=False
        )

    probed = [c.kwargs["query"] for c in page.call_args_list]
    assert probed[:2] == ["a", "b"]
    assert "aa" in probed and "a_" in probed        # 'a' was expanded …
    assert not any(p.startswith("b") and len(p) > 1 for p in probed)   # … 'b' was not
    assert len(found) == sc._PAGE_SIZE + 1
    assert not truncated


def test_prefix_sweep_is_breadth_first_and_bounded():
    """Budget exhaustion must leave full coverage of a level, not depth-first holes."""
    with patch.object(sc, "_page", return_value=(200, [_item("xxx", 2000)] * sc._PAGE_SIZE)) as page:
        _, requests_made, truncated = sc._sweep_by_prefix(
            1000, max_requests=5, prefixes=["a", "b", "c"], sleep=False
        )
    assert requests_made == 5
    assert truncated
    probed = [c.kwargs["query"] for c in page.call_args_list]
    assert probed[:3] == ["a", "b", "c"]           # every depth-1 prefix first
    assert all(len(p) == 2 for p in probed[3:])    # only then depth 2


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


def test_saved_catalog_round_trips_for_offline_refiltering(tmp_path):
    """Dump once, re-filter many times — the sweep is the expensive half."""
    from casino_dashboard.jobs.subreddit_catalog_run import (
        load_catalog_csv,
        write_artifacts,
    )

    csv_path = write_artifacts(_sample_report(), tmp_path, "2026-08-15")[0]
    with patch.object(sc, "_page", side_effect=AssertionError("network touched")):
        reloaded = load_catalog_csv(csv_path)
        report = build_report(_ENTRIES, infos=reloaded, ticker_min_subscribers=50)

    assert [i.name for i in reloaded] == [
        "wallstreetbets", "Stockholm", "RKLB", "RocketLab"
    ]
    assert report.by_ticker() == {"RKLB": ["RKLB", "RocketLab"]}


def test_per_ticker_pass_only_runs_for_stocks_the_sweep_missed():
    """The expensive per-ticker probe is for gaps, not for the whole universe."""
    from casino_dashboard.jobs.subreddit_catalog_run import fill_gaps_with_discovery
    from core.social_media.reddit.subreddit_discovery import DiscoveryResult

    def fake_discover(ticker, company_name=None, sleep=True):
        return DiscoveryResult(
            ticker=ticker,
            subreddits=[ScoredSubreddit(
                info=_info(f"{ticker}_Stock", 22), relevance=0.6, score=1.0, selected=True,
            )],
        )

    with patch("core.social_media.reddit.subreddit_discovery.discover",
               side_effect=fake_discover) as discover:
        filled = fill_gaps_with_discovery(_sample_report(), _ENTRIES, sleep=False)

    # RKLB was already covered by the sweep; only the other two are probed.
    assert sorted(c.args[0] for c in discover.call_args_list) == ["ASTS", "PL"]
    assert filled == {"ASTS": ["ASTS_Stock"], "PL": ["PL_Stock"]}


def test_write_artifacts_dumps_csv_and_json(tmp_path):
    from casino_dashboard.jobs.subreddit_catalog_run import write_artifacts

    paths = write_artifacts(_sample_report(), tmp_path, "2026-08-15")
    csv_text = paths[0].read_text()
    assert "subreddit,subscribers" in csv_text
    assert "wallstreetbets" in csv_text

    payload = json.loads(paths[1].read_text())
    assert payload["tickers"] == {"RKLB": ["RKLB", "RocketLab"]}
    assert payload["strategy"] == "supplied"


# ---------------------------------------------------------------------------
# Phase 1 (fetch) / phase 2 (filter) split
# ---------------------------------------------------------------------------

def test_fetch_only_streams_names_and_counts_without_filtering(tmp_path):
    """Phase 1 writes as it goes and touches neither yfinance nor the filters."""
    from casino_dashboard.jobs.subreddit_catalog_run import fetch_only

    rows = [
        {"display_name": "wallstreetbets", "subscribers": 18_000_000},
        {"display_name": "Stockholm", "subscribers": 210_000},   # kept: no filtering here
        {"display_name": "toosmall", "subscribers": 40},         # below the floor
    ]
    with patch.object(arctic, "iter_subreddits_by_subscribers", return_value=iter(rows)):
        csv_path, written, floor = fetch_only(
            tmp_path, "2026-08-15", min_subscribers=1000, max_requests=5, sleep=False
        )

    text = csv_path.read_text()
    assert text.startswith("subreddit,subscribers,")
    assert "wallstreetbets,18000000" in text
    assert "Stockholm,210000" in text        # phase 1 does not judge
    assert "toosmall" not in text            # but it does respect the floor
    assert (written, floor) == (2, 210_000)


def test_fetch_only_output_feeds_the_filter_phase(tmp_path):
    """The two phases have to actually compose: fetch once, filter from the file."""
    from casino_dashboard.jobs.subreddit_catalog_run import fetch_only, load_catalog_csv

    rows = [
        {"display_name": "RKLB", "subscribers": 41_000, "title": "Rocket Lab",
         "public_description": "Stock discussion for RKLB investors"},
        {"display_name": "Stockholm", "subscribers": 210_000, "title": "Stockholm",
         "public_description": "The capital of Sweden"},
    ]
    with patch.object(arctic, "iter_subreddits_by_subscribers", return_value=iter(rows)):
        csv_path, _, _ = fetch_only(
            tmp_path, "2026-08-15", min_subscribers=1000, max_requests=5, sleep=False
        )

    report = build_report(_ENTRIES, infos=load_catalog_csv(csv_path), ticker_min_subscribers=50)
    assert report.by_ticker() == {"RKLB": ["RKLB"]}
    assert {r.info.name for r in report.market_rows} == {"RKLB"}   # Stockholm dropped


def test_company_names_are_cached_and_only_missing_ones_are_resolved(tmp_path):
    """The Yahoo lookup is the slowest part of a run — it must not repeat."""
    from casino_dashboard.jobs import subreddit_catalog_run as job

    cache = tmp_path / "names.yaml"
    job.save_company_names({"RKLB": "Rocket Lab USA, Inc."}, path=cache)
    assert job.load_company_names(path=cache) == {"RKLB": "Rocket Lab USA, Inc."}

    resolved = []

    def fake_lookup(ticker):
        resolved.append(ticker)
        return f"{ticker} Corp"

    with patch.object(job, "_NAMES_CACHE", cache), \
         patch("casino_dashboard.universe.load_universe") as universe, \
         patch("core.social_media.reddit.ticker_resolver.company_name_for", fake_lookup):
        universe.return_value.all_tickers.return_value = {"RKLB", "ASTS"}
        entries = job.universe_entries()

    assert resolved == ["ASTS"]        # RKLB came from the cache, untouched
    by_ticker = {e.ticker: e.company_name for e in entries}
    assert by_ticker == {"RKLB": "Rocket Lab USA, Inc.", "ASTS": "ASTS Corp"}
    assert job.load_company_names(path=cache)["ASTS"] == "ASTS Corp"   # persisted
