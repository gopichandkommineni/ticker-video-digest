"""Unit tests for the ranked-by-subscriber scan — no real network calls."""
from unittest.mock import patch

from core.social_media.reddit import arctic_shift_client as arctic
from core.social_media.reddit.subreddit_discovery import (
    DiscoveryResult,
    ScoredSubreddit,
    SubredditInfo,
)
from casino_dashboard.jobs import subreddit_rank_scan as scan


# ---------------------------------------------------------------------------
# Arctic Shift ranked-enumeration iterator
# ---------------------------------------------------------------------------

def _fake_search(dataset):
    """Mimic /api/subreddits/search sorted by subscribers desc, with min/max."""
    def fake(query=None, subreddit=None, limit=20,
             min_subscribers=None, max_subscribers=None, sort=None, sort_type=None):
        items = [
            d for d in dataset
            if (min_subscribers is None or d["subscribers"] >= min_subscribers)
            and (max_subscribers is None or d["subscribers"] <= max_subscribers)
        ]
        items.sort(key=lambda d: d["subscribers"], reverse=True)
        return items[:limit]
    return fake


def test_iter_pages_descending_and_respects_floor():
    data = [{"display_name": n, "subscribers": s} for n, s in
            [("A", 500), ("B", 400), ("C", 300), ("D", 200), ("E", 150), ("F", 50)]]
    with patch.object(arctic, "search_subreddits", side_effect=_fake_search(data)):
        out = list(arctic.iter_subreddits_by_subscribers(
            min_subscribers=100, max_count=100, page_size=2, sleep=0))
    names = [d["display_name"] for d in out]
    assert names == ["A", "B", "C", "D", "E"]   # F (50) below floor; strictly descending


def test_iter_dedupes_and_caps_at_max_count():
    data = [{"display_name": n, "subscribers": s} for n, s in
            [("A", 500), ("B", 400), ("C", 300), ("D", 200)]]
    with patch.object(arctic, "search_subreddits", side_effect=_fake_search(data)):
        out = list(arctic.iter_subreddits_by_subscribers(
            min_subscribers=1, max_count=3, page_size=2, sleep=0))
    assert [d["display_name"] for d in out] == ["A", "B", "C"]   # capped at 3, no dupes


def test_iter_stops_when_empty():
    with patch.object(arctic, "search_subreddits", return_value=[]):
        out = list(arctic.iter_subreddits_by_subscribers(min_subscribers=1, sleep=0))
    assert out == []


# ---------------------------------------------------------------------------
# Job helpers
# ---------------------------------------------------------------------------

def test_info_from_dict():
    info = scan._info_from_dict({
        "display_name": "RKLB", "subscribers": 15000,
        "public_description": "Rocket Lab RKLB stock", "over18": False,
    })
    assert info is not None
    assert info.name == "RKLB" and info.subscribers == 15000
    assert scan._info_from_dict({"subscribers": 5}) is None   # no name


def test_tickers_matching_assigns_to_right_ticker():
    info = SubredditInfo(name="RocketLab", subscribers=42000,
                         public_description="Rocket Lab discussion")
    universe = {"RKLB": "Rocket Lab", "COIN": "Coinbase", "IONQ": "IonQ"}
    assert scan._tickers_matching(info, universe) == ["RKLB"]


def test_global_sweep_collects_hits():
    universe = {"RKLB": "Rocket Lab", "COIN": "Coinbase"}
    items = [
        {"display_name": "RocketLab", "subscribers": 42000, "public_description": "Rocket Lab"},
        {"display_name": "worldnews", "subscribers": 30_000_000, "public_description": "news"},
    ]
    with patch.object(scan.arctic, "iter_subreddits_by_subscribers", return_value=iter(items)):
        hits = scan.global_sweep(universe, min_subscribers=1000, sleep=False)
    assert set(hits) == {"RKLB"}                     # worldnews matched nothing
    assert "rocketlab" in hits["RKLB"]


def test_merge_dedupes_and_ranks_by_subscribers():
    # discover() already scored r/RKLB (30k); the sweep adds r/RocketLab (42k).
    pt = [ScoredSubreddit(
        info=SubredditInfo(name="RKLB", subscribers=30000, posts_7d=10),
        relevance=1.0, score=50.0, selected=True, reasons=["selected"])]
    sweep = {"rocketlab": SubredditInfo(
        name="RocketLab", subscribers=42000, public_description="Rocket Lab")}
    with patch.object(scan, "count_recent_posts", return_value=40) as mock_posts:
        rows = scan._merge_ticker("RKLB", "Rocket Lab", pt, sweep, sleep=False)
    assert [r.info.name for r in rows] == ["RocketLab", "RKLB"]   # 42k before 30k
    mock_posts.assert_called_once_with("RocketLab")               # only the new one
    assert rows[0].info.posts_7d == 40


def test_merge_skips_sweep_dupe_of_discover_result():
    pt = [ScoredSubreddit(
        info=SubredditInfo(name="RKLB", subscribers=30000, posts_7d=10),
        relevance=1.0, score=50.0, selected=True, reasons=["selected"])]
    sweep = {"rklb": SubredditInfo(name="RKLB", subscribers=30000)}  # same sub
    with patch.object(scan, "count_recent_posts", return_value=99) as mock_posts:
        rows = scan._merge_ticker("RKLB", "Rocket Lab", pt, sweep, sleep=False)
    assert len(rows) == 1                       # not double-counted
    mock_posts.assert_not_called()              # discover's post count kept


def test_run_both_modes_merges_and_saves(monkeypatch):
    universe = {"RKLB": "Rocket Lab"}
    disc = DiscoveryResult(ticker="RKLB", company_name="Rocket Lab", subreddits=[
        ScoredSubreddit(info=SubredditInfo(name="RKLB", subscribers=30000, posts_7d=10),
                        relevance=1.0, score=50.0, selected=True, reasons=["selected"])])
    sweep_hits = {"RKLB": {"rocketlab": SubredditInfo(
        name="RocketLab", subscribers=42000, public_description="Rocket Lab")}}

    with patch.object(scan, "build_universe", return_value=universe), \
         patch.object(scan, "global_sweep", return_value=sweep_hits), \
         patch.object(scan, "discover", return_value=disc), \
         patch.object(scan, "count_recent_posts", return_value=40):
        lines = scan.run(mode="both", sleep=False, save=False)

    text = "\n".join(lines)
    assert "r/RocketLab" in text and "r/RKLB" in text
    assert "✅ selected" in text
    assert "global floor=`1,000`" in text
