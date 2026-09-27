"""Tests for Reddit subreddit scraping + keyword search (HTTP mocked)."""
import json
import time
from datetime import datetime, timezone

import pytest
from unittest.mock import MagicMock, patch

from core.social_media.base import SocialPost
from core.social_media.reddit import arctic_shift_client as arctic
from core.social_media.reddit import scrape
from core.social_media.reddit.scrape import (
    DEFAULT_SEARCH_SUBREDDITS,
    matched_keywords,
    scrape_subreddits,
    search_reddit,
)
from casino_dashboard.jobs import reddit_scrape as job

_GET = "core.social_media.reddit.arctic_shift_client.requests.get"


def _resp(status=200, payload=None):
    m = MagicMock()
    m.status_code = status
    m.headers = {}
    m.json.return_value = payload if payload is not None else {"data": []}
    return m


def _item(pid, sub="RKLB", score=1, ncomments=0, age_hours=1.0, title="t", body="b"):
    return {
        "id": pid, "subreddit": sub, "title": title, "selftext": body,
        "score": score, "num_comments": ncomments, "author": "u",
        "permalink": f"/r/{sub}/comments/{pid}/x/",
        "created_utc": time.time() - age_hours * 3600,
    }


def _post(title="", content=""):
    return SocialPost(
        platform="reddit", post_id="p", author="u", title=title, content=content,
        url="u", published_at=datetime.now(tz=timezone.utc), ticker="",
    )


# --- keyword matching ----------------------------------------------------------

@pytest.mark.parametrize("text,kw,hit", [
    ("PATH calls printing", "PATH", True),
    ("loaded up on $PATH", "PATH", True),
    ("Paired-Path Simulation for options", "PATH", False),
    ("career path advice", "PATH", False),
    ("bought $RKLB today", "$RKLB", True),
    ("RKLB to the moon", "$RKLB", True),
    ("RKLBX is different", "RKLB", False),
    ("Rocket  Lab launches Neutron", "rocket lab", True),
    ("rocketlabs merch", "rocket lab", False),
])
def test_keyword_whole_word_matching(text, kw, hit):
    assert (matched_keywords(_post(title=text), [kw]) == [kw]) is hit


def test_matched_keywords_checks_body_and_returns_all_hits():
    p = _post(title="Neutron update", content="Rocket Lab slipped the date")
    assert matched_keywords(p, ["Neutron", "rocket lab", "ASTS"]) == ["Neutron", "rocket lab"]


# --- pagination ----------------------------------------------------------------

def test_paged_search_walks_before_cursor_and_dedupes():
    page1 = {"data": [_item(f"a{i}", age_hours=i) for i in range(100)]}
    # Second page repeats the boundary post, then two new ones (short page = end).
    page2 = {"data": [_item("a99", age_hours=99), _item("b1", age_hours=120),
                      _item("b2", age_hours=121)]}
    with patch(_GET, side_effect=[_resp(payload=page1), _resp(payload=page2)]) as g, \
         patch.object(arctic.time, "sleep"):
        status, items = arctic.search_posts_paged(subreddit="RKLB")
    assert status == 200 and len(items) == 102
    second_params = g.call_args_list[1].kwargs["params"]
    assert second_params["before"] == int(page1["data"][-1]["created_utc"])


def test_paged_search_respects_max_items():
    page = {"data": [_item(f"a{i}", age_hours=i) for i in range(100)]}
    with patch(_GET, return_value=_resp(payload=page)) as g:
        _, items = arctic.search_posts_paged(subreddit="RKLB", max_items=30)
    assert len(items) == 30 and g.call_count == 1


def test_paged_search_reports_rejection_status():
    with patch(_GET, return_value=_resp(status=400)):
        assert arctic.search_posts_paged(query="rocket lab") == (400, [])


# --- subreddit scrape --------------------------------------------------------------

def test_scrape_subreddits_ranks_by_score_with_no_text_filter():
    items = {"data": [
        _item("new_low", score=1, age_hours=1, title="BlueBird launch news"),
        _item("old_high", score=500, age_hours=90, title="Daily thread"),
        _item("mid", score=40, age_hours=10, title="Chart"),
    ]}
    with patch(_GET, return_value=_resp(payload=items)):
        res = scrape_subreddits(["r/ASTSpaceMobile"], limit=2, ticker="ASTS")
    assert res.targets == ["ASTSpaceMobile"]
    assert [sp.post.post_id for sp in res.posts] == ["old_high", "mid"]
    assert all(sp.post.ticker == "ASTS" for sp in res.posts)
    assert res.warnings == []


@pytest.mark.parametrize("sort,first", [("new", "a"), ("comments", "c"), ("top", "b")])
def test_scrape_sort_orders(sort, first):
    items = {"data": [
        _item("a", score=1, ncomments=1, age_hours=1),
        _item("b", score=90, ncomments=2, age_hours=5),
        _item("c", score=5, ncomments=300, age_hours=9),
    ]}
    with patch(_GET, return_value=_resp(payload=items)):
        res = scrape_subreddits(["RKLB"], sort=sort)
    assert res.posts[0].post.post_id == first


def test_scrape_keeps_full_body():
    long_body = "x" * 10_000
    with patch(_GET, return_value=_resp(payload={"data": [_item("a", body=long_body)]})):
        res = scrape_subreddits(["RKLB"])
    assert len(res.posts[0].post.content) == 10_000


def test_scrape_warns_on_empty_and_failed_subs():
    with patch(_GET, side_effect=[_resp(payload={"data": []}), _resp(status=500)]):
        res = scrape_subreddits(["quiet", "broken"])
    assert res.posts == []
    assert any("r/quiet" in w and "no posts" in w for w in res.warnings)
    assert any("r/broken" in w and "500" in w for w in res.warnings)


def test_scrape_attaches_top_comments():
    posts = {"data": [_item("p1", score=10)]}
    comments = {"data": [
        {"id": "c1", "body": "meh", "score": 2, "author": "a", "created_utc": time.time()},
        {"id": "c2", "body": "great DD", "score": 50, "author": "b", "created_utc": time.time()},
        {"id": "c3", "body": "[deleted]", "score": 99, "author": "c", "created_utc": time.time()},
    ]}
    with patch(_GET, side_effect=[_resp(payload=posts), _resp(payload=comments)]) as g:
        res = scrape_subreddits(["RKLB"], comments_per_post=1)
    assert [c.body for c in res.posts[0].comments] == ["great DD"]
    assert g.call_args_list[1].kwargs["params"]["link_id"] == "p1"


def test_comments_retry_with_t3_prefix():
    with patch(_GET, side_effect=[_resp(payload={"data": []}),
                                  _resp(payload={"data": [{"id": "c"}]})]) as g:
        assert arctic.search_comments("abc") == [{"id": "c"}]
    assert g.call_args_list[1].kwargs["params"]["link_id"] == "t3_abc"


# --- keyword search ----------------------------------------------------------------

def test_search_in_named_subreddits_drops_substring_hits():
    items = {"data": [
        _item("real", sub="wallstreetbets", score=30, title="PATH earnings play"),
        _item("noise", sub="wallstreetbets", score=900, title="Paired-Path Simulation"),
    ]}
    with patch(_GET, return_value=_resp(payload=items)) as g:
        res = search_reddit(["PATH"], subreddits=["wallstreetbets"])
    assert [sp.post.post_id for sp in res.posts] == ["real"]
    assert res.posts[0].matched_keywords == ["PATH"]
    assert res.subreddits == ["wallstreetbets"]
    params = g.call_args.kwargs["params"]
    assert params["subreddit"] == "wallstreetbets" and params["query"] == "PATH"


def test_search_strips_dollar_for_the_archive_query():
    with patch(_GET, return_value=_resp(payload={"data": []})) as g:
        search_reddit(["$RKLB"], subreddits=["stocks"])
    assert g.call_args.kwargs["params"]["query"] == "RKLB"


def test_search_reddit_wide_when_archive_allows():
    items = {"data": [_item("a", sub="SpaceX", title="Rocket Lab vs SpaceX")]}
    with patch(_GET, return_value=_resp(payload=items)) as g:
        res = search_reddit(["rocket lab"])
    assert "subreddit" not in g.call_args.kwargs["params"]
    assert res.subreddits == ["(all of Reddit)"] and res.warnings == []
    assert res.posts[0].post.subreddit == "SpaceX"


def test_search_falls_back_to_default_subs_when_reddit_wide_refused():
    hit = {"data": [_item("a", sub="stocks", title="Rocket Lab")]}

    def fake_get(url, params, **_):
        if "subreddit" not in params:
            return _resp(status=400)
        return _resp(payload=hit if params["subreddit"] == "stocks" else {"data": []})

    with patch(_GET, side_effect=fake_get) as g:
        res = search_reddit(["rocket lab", "Neutron"])
    assert res.subreddits == DEFAULT_SEARCH_SUBREDDITS
    assert len(res.warnings) == 1 and "HTTP 400" in res.warnings[0]
    assert [sp.post.post_id for sp in res.posts] == ["a"]
    # The second keyword goes straight to the fallback subs — no second 400.
    reddit_wide = [c for c in g.call_args_list if "subreddit" not in c.kwargs["params"]]
    assert len(reddit_wide) == 1


def test_search_dedupes_posts_hit_by_several_keywords():
    items = {"data": [_item("a", title="Rocket Lab Neutron")]}
    with patch(_GET, return_value=_resp(payload=items)):
        res = search_reddit(["rocket lab", "Neutron"], subreddits=["RKLB"])
    assert len(res.posts) == 1
    assert res.posts[0].matched_keywords == ["rocket lab", "Neutron"]


# --- CLI -------------------------------------------------------------------------------

def test_cli_search_writes_report_json_and_step_summary(tmp_path, monkeypatch, capsys):
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    out = tmp_path / "out" / "r.json"
    items = {"data": [_item("a", sub="stocks", score=12, title="IREN | capacity update")]}
    with patch(_GET, return_value=_resp(payload=items)):
        job.main(["search", "IREN", "--subreddits", "stocks,investing", "--json", str(out)])
    printed = capsys.readouterr().out
    assert "## Reddit search" in printed and "IREN \\| capacity update" in printed
    assert "Searched: stocks, investing" in printed
    assert summary.read_text().startswith("## Reddit search")
    data = json.loads(out.read_text())
    assert data["mode"] == "search" and data["posts"][0]["post"]["post_id"] == "a"


def test_cli_subreddit_accepts_comma_list():
    args = job._parse_args(["subreddit", "RKLB,ASTSpaceMobile"])
    with patch.object(job, "scrape_subreddits") as s:
        job.run(args)
    assert s.call_args.args[0] == ["RKLB", "ASTSpaceMobile"]


def test_cli_save_requires_ticker():
    with pytest.raises(SystemExit):
        job._parse_args(["subreddit", "RKLB", "--save"])


def test_cli_rejects_subreddits_flag_in_subreddit_mode():
    with pytest.raises(SystemExit):
        job._parse_args(["subreddit", "RKLB", "--subreddits", "stocks"])


def test_cli_save_writes_reddit_posts(tmp_path):
    from casino_dashboard.db.repository import get_recent_reddit_posts

    db = tmp_path / "t.db"
    with patch(_GET, return_value=_resp(payload={"data": [_item("a", score=3)]})):
        res = scrape_subreddits(["RKLB"], ticker="RKLB")
    assert job._save(res, db) == 1
    df = get_recent_reddit_posts("RKLB", db_path=db)
    assert list(df["post_id"]) == ["a"]


def test_render_report_handles_no_posts():
    res = scrape.ScrapeResult(mode="subreddit", targets=["x"], days_back=7, sort="top",
                              warnings=["r/x: no posts in the last 7 days"])
    lines = job.render_report(res)
    assert "_No posts found._" in lines and any("⚠️" in line for line in lines)


def test_unreachable_archive_is_worded_plainly():
    with patch(_GET, side_effect=ConnectionError("blocked")):
        res = scrape_subreddits(["RKLB"])
    assert res.warnings == ["r/RKLB: archive unreachable (network error)"]
