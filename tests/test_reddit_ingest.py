"""Tests for Reddit ingestion into reddit.db (fake Reddit client, no network)."""
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from core.social_media.base import SocialPost
from core.social_media.reddit.ingest import IngestConfig, run_ingest, short_company_name, ticker_keywords
from core.social_media.reddit.ingest import db
from core.social_media.reddit.scrape import (
    DEFAULT_SEARCH_SUBREDDITS,
    RedditComment,
    ScrapedPost,
    ScrapeResult,
)
from casino_dashboard.jobs import reddit_ingest as job

NOW = datetime(2026, 9, 27, 7, 0, tzinfo=timezone.utc)
CFG = IngestConfig(request_delay=0)


def _post(pid, sub="RKLB", score=1, ncom=0, age_h=10, title="t", body="b", ticker="RKLB", hits=()):
    return ScrapedPost(
        post=SocialPost(platform="reddit", post_id=pid, author="u", title=title, content=body,
                        url=f"https://reddit.com/r/{sub}/comments/{pid}", subreddit=sub,
                        published_at=NOW - timedelta(hours=age_h), score=score,
                        comment_count=ncom, ticker=ticker),
        matched_keywords=list(hits),
    )


def _result(posts=(), warnings=(), mode="subreddit"):
    return ScrapeResult(mode=mode, targets=[], days_back=7, sort="new",
                        posts=list(posts), warnings=list(warnings))


class FakeClient:
    """Stands in for the `scrape` module; records every call."""

    def __init__(self, feed=None, search=None, comments=None, fail=()):
        self.feed, self.search, self.comments = feed or {}, search or {}, comments or {}
        self.fail = set(fail)
        self.calls = []

    def scrape_subreddits(self, subs, **kw):
        self.calls.append(("feed", kw["ticker"], tuple(subs), kw["days_back"]))
        if kw["ticker"] in self.fail:
            raise RuntimeError("boom")
        return self.feed.get(kw["ticker"], _result())

    def search_reddit(self, keywords, subreddits=None, **kw):
        self.calls.append(("search", kw["ticker"], tuple(keywords), tuple(subreddits)))
        if kw["ticker"] in self.fail:
            raise RuntimeError("boom")
        return self.search.get(kw["ticker"], _result(mode="search"))

    def fetch_top_comments(self, post_id, limit):
        self.calls.append(("comments", post_id, limit))
        return self.comments.get(post_id, [])


def _rows(path, sql, *args):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(sql, args)]
    finally:
        conn.close()


@pytest.fixture
def path(tmp_path) -> Path:
    return tmp_path / "reddit.db"


# --- keywords --------------------------------------------------------------------

@pytest.mark.parametrize("raw,short", [
    ("Applied Optoelectronics, Inc.", "Applied Optoelectronics"),
    ("Rocket Lab Corporation", "Rocket Lab"),
    ("IonQ, Inc.", "IonQ"),
    ("The Walt Disney Company", "Walt Disney"),
    ("First Majestic Silver Corp.", "First Majestic Silver"),
    (None, None),
    ("Co.", None),
])
def test_short_company_name(raw, short):
    assert short_company_name(raw) == short


def test_ticker_keywords():
    assert ticker_keywords("RKLB", "Rocket Lab Corporation") == ["RKLB", "Rocket Lab"]
    assert ticker_keywords("IONQ", "IonQ, Inc.") == ["IONQ"]         # name == ticker
    assert ticker_keywords("XYZ", None) == ["XYZ"]


# --- a first run ------------------------------------------------------------------

def test_first_run_stores_feed_and_search_posts(path):
    client = FakeClient(
        feed={"RKLB": _result([_post("f1", sub="RocketLab", score=40)])},
        search={"RKLB": _result([_post("s1", sub="stocks", hits=["RKLB"])], mode="search")},
    )
    rep = run_ingest(["rklb"], {"RKLB": ["RocketLab", "RKLB"]}, ["stocks"],
                     {"RKLB": "Rocket Lab Corporation"}, db_path=path, cfg=CFG, now=NOW, client=client)

    assert rep.status == "ok" and rep.days_back == 7
    assert rep.posts_new == 2 and rep.per_ticker["RKLB"].feed == 1 and rep.per_ticker["RKLB"].search == 1
    assert ("feed", "RKLB", ("RocketLab", "RKLB"), 7) in client.calls
    assert ("search", "RKLB", ("RKLB", "Rocket Lab"), ("stocks",)) in client.calls
    links = {r["post_id"]: r for r in _rows(path, "SELECT * FROM post_tickers")}
    assert links["f1"]["via"] == "subreddit" and links["f1"]["matched"] == "RocketLab"
    assert links["s1"]["via"] == "search" and links["s1"]["matched"] == "RKLB"
    run = _rows(path, "SELECT * FROM runs")[0]
    assert run["status"] == "ok" and run["posts_new"] == 2 and run["finished_at"]


def test_unmapped_stock_is_only_searched(path):
    client = FakeClient()
    run_ingest(["ASTS"], {}, [], {}, db_path=path, cfg=CFG, now=NOW, client=client)
    kinds = [c[0] for c in client.calls]
    assert kinds == ["search"]
    assert client.calls[0][3] == tuple(DEFAULT_SEARCH_SUBREDDITS)   # empty general list


def test_body_is_capped(path):
    client = FakeClient(feed={"RKLB": _result([_post("f1", body="x" * 50_000)])})
    run_ingest(["RKLB"], {"RKLB": ["RKLB"]}, [], {}, db_path=path, cfg=CFG, now=NOW, client=client)
    assert len(_rows(path, "SELECT body FROM posts")[0]["body"]) == CFG.body_chars


# --- re-runs ----------------------------------------------------------------------

def test_rerun_window_overlap_and_score_history(path):
    first = FakeClient(feed={"RKLB": _result([_post("f1", score=0)])})
    run_ingest(["RKLB"], {"RKLB": ["RKLB"]}, [], {}, db_path=path, cfg=CFG, now=NOW, client=first)

    later = NOW + timedelta(days=1)
    second = FakeClient(feed={"RKLB": _result([_post("f1", score=0)])})
    rep = run_ingest(["RKLB"], {"RKLB": ["RKLB"]}, [], {}, db_path=path, cfg=CFG, now=later, client=second)
    # Window = last good run (NOW) - 3 days overlap → 4 days back.
    assert rep.days_back == 4 and rep.posts_new == 0 and rep.posts_updated == 1
    assert len(_rows(path, "SELECT * FROM post_scores")) == 1      # unchanged score: no new row

    third = FakeClient(feed={"RKLB": _result([_post("f1", score=55, ncom=9)])})
    run_ingest(["RKLB"], {"RKLB": ["RKLB"]}, [], {}, db_path=path, cfg=CFG,
               now=later + timedelta(days=1), client=third)
    scores = _rows(path, "SELECT score FROM post_scores ORDER BY seen_at")
    assert [s["score"] for s in scores] == [0, 55]
    assert _rows(path, "SELECT score, num_comments FROM posts")[0] == {"score": 55, "num_comments": 9}


def test_fixed_window_reads_exactly_the_last_n_days(path):
    """On demand (--days): the window ignores the last run and its overlap."""
    run_ingest([], {}, [], {}, db_path=path, cfg=CFG, now=NOW, client=FakeClient())
    fixed = CFG.model_copy(update={"window_days": 7})
    rep = run_ingest([], {}, [], {}, db_path=path, cfg=fixed, now=NOW + timedelta(hours=2),
                     client=FakeClient())
    assert rep.days_back == 7


def test_job_days_flag_sets_the_fixed_window(tmp_path, monkeypatch):
    monkeypatch.setenv("REDDIT_DB_PATH", str(tmp_path / "r.db"))
    monkeypatch.setattr(job, "load_subreddit_map", lambda: {})
    monkeypatch.setattr(job, "load_general_subreddits", lambda: [])
    monkeypatch.setattr(job, "load_company_names", lambda: {})
    seen = {}

    def fake_run(tickers, *a, cfg=None, **k):
        seen["tickers"], seen["cfg"] = tickers, cfg
        return run_ingest(tickers, {}, [], {}, cfg=CFG, client=FakeClient())
    monkeypatch.setattr(job, "run_ingest", fake_run)
    job.main(["--days", "7", "rklb"])
    assert seen["tickers"] == ["RKLB"] and seen["cfg"].window_days == 7
    job.main(["RKLB"])
    assert seen["cfg"] is None                     # scheduled runs keep "since last run"


def test_window_is_capped_after_a_long_gap(path):
    run_ingest([], {}, [], {}, db_path=path, cfg=CFG, now=NOW, client=FakeClient())
    rep = run_ingest([], {}, [], {}, db_path=path, cfg=CFG, now=NOW + timedelta(days=60),
                     client=FakeClient())
    assert rep.days_back == CFG.max_window_days


def test_subreddit_link_beats_search_link(path):
    client = FakeClient(
        feed={"RKLB": _result([_post("p1", sub="RKLB")])},
        search={"RKLB": _result([_post("p1", sub="RKLB", hits=["RKLB"])], mode="search")},
    )
    run_ingest(["RKLB"], {"RKLB": ["RKLB"]}, [], {}, db_path=path, cfg=CFG, now=NOW, client=client)
    link = _rows(path, "SELECT via, matched FROM post_tickers")
    assert link == [{"via": "subreddit", "matched": "RKLB"}]


# --- noisy tickers ------------------------------------------------------------------

def test_noisy_ticker_search_needs_dollar_or_company(path):
    client = FakeClient(search={"PATH": _result([
        _post("plain", title="PATH is up", hits=["PATH"], ticker="PATH"),
        _post("dollar", title="Loaded $PATH calls", hits=["PATH"], ticker="PATH"),
        _post("name", title="UiPath earnings", hits=["UiPath"], ticker="PATH"),
    ], mode="search")})
    run_ingest(["PATH"], {}, [], {"PATH": "UiPath, Inc."}, db_path=path, cfg=CFG, now=NOW, client=client)
    kept = {r["post_id"] for r in _rows(path, "SELECT post_id FROM posts")}
    assert kept == {"dollar", "name"}


# --- comments -----------------------------------------------------------------------

def _comment(cid, parent, score=5):
    return RedditComment(comment_id=cid, author="a", body="c" * 3000, score=score,
                         published_at=NOW, url="", parent_id=parent)


def test_comments_fetched_for_notable_posts_only(path):
    client = FakeClient(
        feed={"RKLB": _result([_post("busy", ncom=300), _post("quiet", score=2, ncom=1)])},
        comments={"busy": [_comment("c1", "t3_busy"), _comment("c2", "t1_c1")]},
    )
    rep = run_ingest(["RKLB"], {"RKLB": ["RKLB"]}, [], {}, db_path=path, cfg=CFG, now=NOW, client=client)
    assert rep.comments_saved == 2
    assert [c for c in client.calls if c[0] == "comments"] == [("comments", "busy", CFG.top_comments)]
    rows = {r["comment_id"]: r for r in _rows(path, "SELECT * FROM comments")}
    assert rows["c2"]["parent_id"] == "t1_c1" and rows["c1"]["post_id"] == "busy"
    assert len(rows["c1"]["body"]) == CFG.comment_chars


def test_comments_refetched_while_fresh_then_left_alone(path):
    feed = {"RKLB": _result([_post("busy", ncom=300, age_h=10)])}
    run_ingest(["RKLB"], {"RKLB": ["RKLB"]}, [], {}, db_path=path, cfg=CFG, now=NOW,
               client=FakeClient(feed=feed))

    soon = FakeClient(feed=feed)          # 2h later: fetched too recently
    run_ingest(["RKLB"], {"RKLB": ["RKLB"]}, [], {}, db_path=path, cfg=CFG,
               now=NOW + timedelta(hours=2), client=soon)
    assert not [c for c in soon.calls if c[0] == "comments"]

    next_day = FakeClient(feed=feed)      # a day on, post still < 3 days old
    run_ingest(["RKLB"], {"RKLB": ["RKLB"]}, [], {}, db_path=path, cfg=CFG,
               now=NOW + timedelta(days=1), client=next_day)
    assert [c for c in next_day.calls if c[0] == "comments"]

    week_on = FakeClient()                # post now a week old: thread considered settled
    run_ingest(["RKLB"], {"RKLB": ["RKLB"]}, [], {}, db_path=path, cfg=CFG,
               now=NOW + timedelta(days=7), client=week_on)
    assert not [c for c in week_on.calls if c[0] == "comments"]


# --- pruning ------------------------------------------------------------------------

def test_prune_drops_old_and_quiet_posts_with_their_rows(path):
    client = FakeClient(
        feed={"RKLB": _result([
            _post("ancient", score=500, ncom=200, age_h=24 * 100),
            _post("quiet_old", score=1, ncom=0, age_h=24 * 20),
            _post("quiet_new", score=1, ncom=0, age_h=24 * 2),
            _post("busy_old", score=80, ncom=40, age_h=24 * 20),
        ])},
        comments={"ancient": [_comment("c1", "t3_ancient")]},
    )
    rep = run_ingest(["RKLB"], {"RKLB": ["RKLB"]}, [], {}, db_path=path, cfg=CFG, now=NOW, client=client)
    assert rep.pruned == 2
    assert {r["post_id"] for r in _rows(path, "SELECT post_id FROM posts")} == {"quiet_new", "busy_old"}
    for table in ("comments", "post_scores", "post_tickers"):
        ids = {r["post_id"] for r in _rows(path, f"SELECT post_id FROM {table}")}
        assert not ids & {"ancient", "quiet_old"}, table


# --- failures -----------------------------------------------------------------------

def test_one_failing_stock_makes_a_partial_run(path):
    client = FakeClient(feed={"ASTS": _result([_post("a1", sub="ASTSpaceMobile")])}, fail={"RKLB"})
    rep = run_ingest(["RKLB", "ASTS"], {"RKLB": ["RKLB"], "ASTS": ["ASTSpaceMobile"]}, [], {},
                     db_path=path, cfg=CFG, now=NOW, client=client)
    assert rep.status == "partial" and rep.posts_new == 1
    assert any(e.startswith("RKLB:") for e in rep.errors)


def test_archive_down_is_a_failed_run_and_does_not_advance_the_window(path):
    down = _result(warnings=["r/RKLB: archive unreachable (network error)"])
    client = FakeClient(feed={"RKLB": down},
                        search={"RKLB": _result(warnings=["Reddit-wide search unavailable"], mode="search")})
    rep = run_ingest(["RKLB"], {"RKLB": ["RKLB"]}, [], {}, db_path=path, cfg=CFG, now=NOW, client=client)
    assert rep.status == "failed" and len(rep.errors) == 2
    conn = db.connect(path)
    assert db.last_good_run_start(conn) is None      # next run still reads a full week
    conn.close()


def test_quiet_subreddit_is_not_an_error(path):
    client = FakeClient(feed={"RKLB": _result(warnings=["r/RKLB: no posts in the last 7 days"])})
    rep = run_ingest(["RKLB"], {"RKLB": ["RKLB"]}, [], {}, db_path=path, cfg=CFG, now=NOW, client=client)
    assert rep.status == "ok" and rep.errors == []


# --- the job ------------------------------------------------------------------------

def test_job_runs_and_reports(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("REDDIT_DB_PATH", str(tmp_path / "r.db"))
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    fake = FakeClient(feed={"RKLB": _result([_post("f1")])})
    monkeypatch.setattr(job, "load_subreddit_map", lambda: {"RKLB": ["RKLB"]})
    monkeypatch.setattr(job, "load_general_subreddits", lambda: [])
    monkeypatch.setattr(job, "load_company_names", lambda: {})
    real = job.run_ingest
    monkeypatch.setattr(job, "run_ingest",
                        lambda *a, cfg=None, **k: real(*a, cfg=cfg or CFG, client=fake, **k))
    assert job.main(["RKLB", "ASTS"]) == 0
    out = capsys.readouterr().out
    assert "## Reddit ingest — ✅ ok" in out
    assert "| RKLB | 1 | 0 |" in out and "| ASTS | — (none mapped) | 0 |" in out
    assert summary.read_text().startswith("## Reddit ingest")
    assert (tmp_path / "r.db").exists()


def test_default_db_path_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("REDDIT_DB_PATH", str(tmp_path / "x.db"))
    assert db.default_db_path() == tmp_path / "x.db"
    monkeypatch.delenv("REDDIT_DB_PATH")
    assert db.default_db_path().parts[-2:] == ("data", "reddit.db")
