"""PR B — production cutover: ingest_handle routes through the worker pool.

Parity (sequential vs pool), mismatch reopen, handle-scoping, ingest_all
routing, and ingest_all isolation. Never hits a real provider — adapters are
faked and patched into both the sequential (`day_fetcher.get_source`) and pool
(`tweet_sources.factory.get_source`) seams.
"""

from __future__ import annotations

import datetime
from pathlib import Path
from unittest.mock import patch

from fintwit.storage.db import init_db, get_connection
from fintwit.storage.handles import get_handle
from fintwit.orchestration.runner import ingest_handle, ingest_all
from fintwit.orchestration.day_fetcher import DayFetchSummary
from fintwit.tweet_sources.base import Tweet, FetchResult, UserInfo

UTC = datetime.timezone.utc


# ---------------------------------------------------------------------------
# Fakes / helpers
# ---------------------------------------------------------------------------

def _tweet(tid: str, created: str) -> Tweet:
    return Tweet(
        id=tid, created_at_utc=created, text=f"t{tid}", type="original",
        is_reply=False, is_quote=False, in_reply_to_id=None, quoted_tweet_id=None,
        quoted_author_id=None, conversation_id=None, like_count=0, retweet_count=0,
        reply_count=0, quote_count=0, view_count=None, bookmark_count=None,
        has_media=False, media_urls=[], url=None,
    )


class FakeSource:
    def __init__(self, by_day: dict[str, list[Tweet]], provider_name: str):
        self.by_day = by_day
        self.provider_name = provider_name
        self.calls: list[tuple[str, datetime.date]] = []

    def fetch_user_info(self, handle: str) -> UserInfo:
        return UserInfo(handle=handle, display_name="F", user_id="1", created_at_utc=None,
                        followers_count=0, following_count=0, bio=None,
                        is_verified=False, is_blue_verified=False)

    def fetch_tweets(self, handle, start, end) -> FetchResult:
        self.calls.append((handle, start))
        return FetchResult(tweets=self.by_day.get(start.isoformat(), []), reached_floor=True)


def _get_source_factory(gx: FakeSource, tw: FakeSource):
    def _get(provider: str):
        return gx if provider == "getxapi" else tw
    return _get


def _patch_both(gx: FakeSource, tw: FakeSource):
    """Patch the adapter into both the sequential and pool resolution seams."""
    gs = _get_source_factory(gx, tw)
    return (
        patch("fintwit.orchestration.day_fetcher.get_source", side_effect=gs),
        patch("fintwit.tweet_sources.factory.get_source", side_effect=gs),
        patch("fintwit.orchestration.day_fetcher.INTER_DAY_DELAY", 0.0),
    )


def _fresh(tmp_path: Path, name: str) -> Path:
    db = tmp_path / name
    init_db(db)
    return db


def _seed_handle_with_history(db: Path, handle: str, ok_dates: list[str]) -> None:
    """Seed a 'ready' handle plus prior 'ok' day rows so ingest_handle takes the
    delta path. The prior-history rows are what surface the days_* semantic shift
    (plan §5)."""
    conn = get_connection(db)
    try:
        with conn:
            conn.execute(
                "INSERT OR IGNORE INTO handles (handle, status, total_tweets) "
                "VALUES (?, 'ready', 0)", (handle,))
            for d in ok_dates:
                for p in ("getxapi", "twitterapi"):
                    conn.execute(
                        "INSERT OR IGNORE INTO day_fetch_log "
                        "(handle, date, provider, status, tweet_count, retry_count) "
                        "VALUES (?, ?, ?, 'ok', 5, 0)", (handle, d, p))
    finally:
        conn.close()


def _set_day(db: Path, handle: str, date: str, provider: str, status: str,
             retry_count: int = 0, tweet_count: int | None = None) -> None:
    conn = get_connection(db)
    try:
        with conn:
            conn.execute(
                "INSERT OR IGNORE INTO day_fetch_log "
                "(handle, date, provider, status) VALUES (?, ?, ?, ?)",
                (handle, date, provider, status))
            conn.execute(
                "UPDATE day_fetch_log SET status=?, retry_count=?, tweet_count=? "
                "WHERE handle=? AND date=? AND provider=?",
                (status, retry_count, tweet_count, handle, date, provider))
    finally:
        conn.close()


def _rows(db: Path, handle: str | None = None):
    conn = get_connection(db)
    try:
        if handle:
            q = ("SELECT handle, date, provider, status FROM day_fetch_log "
                 "WHERE handle=? ORDER BY date, provider")
            return [tuple(r) for r in conn.execute(q, (handle,)).fetchall()]
        q = "SELECT handle, date, provider, status FROM day_fetch_log ORDER BY handle, date, provider"
        return [tuple(r) for r in conn.execute(q).fetchall()]
    finally:
        conn.close()


def _day_row(db: Path, handle: str, date: str, provider: str) -> dict:
    conn = get_connection(db)
    try:
        r = conn.execute(
            "SELECT status, retry_count FROM day_fetch_log "
            "WHERE handle=? AND date=? AND provider=?", (handle, date, provider)).fetchone()
        return dict(r) if r else {}
    finally:
        conn.close()


def _window_by_day():
    """Three in-window days: today ok, yesterday mismatch (3 vs 1), 2-days-ago empty(ok)."""
    today = datetime.date.today()
    d1 = (today - datetime.timedelta(days=1)).isoformat()
    d2 = (today - datetime.timedelta(days=2)).isoformat()
    t = today.isoformat()
    gx = {
        t:  [_tweet("g1", f"{t}T10:00:00Z"), _tweet("g2", f"{t}T11:00:00Z")],
        d1: [_tweet("g3", f"{d1}T10:00:00Z"), _tweet("g4", f"{d1}T11:00:00Z"),
             _tweet("g5", f"{d1}T12:00:00Z")],
        d2: [],
    }
    tw = {
        t:  [_tweet("g1", f"{t}T10:00:00Z"), _tweet("g2", f"{t}T11:00:00Z")],
        d1: [_tweet("g3", f"{d1}T10:00:00Z")],          # 1 vs 3 → mismatch
        d2: [],
    }
    return gx, tw, t, d1, d2


# ---------------------------------------------------------------------------
# Parity — the most important test
# ---------------------------------------------------------------------------

def test_ingest_handle_parity_sequential_vs_pool(tmp_path):
    gx_map, tw_map, t, d1, d2 = _window_by_day()
    today = datetime.date.today()
    prior = [(today - datetime.timedelta(days=n)).isoformat() for n in (5, 4, 3)]

    def run(db, sequential):
        gx = FakeSource(gx_map, "getxapi")
        tw = FakeSource(tw_map, "twitterapi")
        _seed_handle_with_history(db, "h", prior)
        p_seq, p_fac, p_delay = _patch_both(gx, tw)
        with p_seq, p_fac, p_delay:
            return ingest_handle("h", db_path=db, sequential=sequential)

    db_seq = _fresh(tmp_path, "seq.db")
    db_pool = _fresh(tmp_path, "pool.db")
    res_seq = run(db_seq, True)
    res_pool = run(db_pool, False)

    # Identical final ledger state per (handle, date, provider, status).
    assert _rows(db_seq, "h") == _rows(db_pool, "h"), (
        f"seq={_rows(db_seq, 'h')} pool={_rows(db_pool, 'h')}")
    # Identical outcome and handle status.
    assert res_seq.outcome == res_pool.outcome
    assert get_handle("h", db_path=db_seq)["status"] == get_handle("h", db_path=db_pool)["status"]

    # Fixture exercises both verdicts: yesterday mismatch, today ok.
    assert _day_row(db_pool, "h", d1, "getxapi")["status"] == "mismatch"
    assert _day_row(db_pool, "h", t, "getxapi")["status"] == "ok"
    assert res_pool.outcome == "incomplete"   # the mismatch day is outstanding


# ---------------------------------------------------------------------------
# Mismatch reopen
# ---------------------------------------------------------------------------

def test_mismatch_reopened_when_under_max_attempts(tmp_path):
    db = _fresh(tmp_path, "m.db")
    today = datetime.date.today()
    prior = [(today - datetime.timedelta(days=n)).isoformat() for n in (5, 4, 3)]
    _seed_handle_with_history(db, "h", prior)

    # A prior mismatch day OUTSIDE the 3-day window, retry_count=1 (under cap).
    old = (today - datetime.timedelta(days=10)).isoformat()
    for p in ("getxapi", "twitterapi"):
        _set_day(db, "h", old, p, "mismatch", retry_count=1, tweet_count=9)

    # Adapter now returns agreeing counts for the old day → it should heal to ok.
    gx = FakeSource({old: [_tweet("x1", f"{old}T10:00:00Z")]}, "getxapi")
    tw = FakeSource({old: [_tweet("x1", f"{old}T10:00:00Z")]}, "twitterapi")
    with patch("fintwit.tweet_sources.factory.get_source", side_effect=_get_source_factory(gx, tw)):
        ingest_handle("h", db_path=db, sequential=False)

    r = _day_row(db, "h", old, "getxapi")
    assert r["status"] == "ok", r            # reopened, re-fetched, re-verdicted
    assert r["retry_count"] == 2             # claim incremented the attempt


def test_terminal_mismatch_not_reopened(tmp_path):
    db = _fresh(tmp_path, "mt.db")
    today = datetime.date.today()
    prior = [(today - datetime.timedelta(days=n)).isoformat() for n in (5, 4, 3)]
    _seed_handle_with_history(db, "h", prior)

    old = (today - datetime.timedelta(days=10)).isoformat()
    for p in ("getxapi", "twitterapi"):
        _set_day(db, "h", old, p, "mismatch", retry_count=3, tweet_count=9)  # at cap

    gx = FakeSource({}, "getxapi")
    tw = FakeSource({}, "twitterapi")
    with patch("fintwit.tweet_sources.factory.get_source", side_effect=_get_source_factory(gx, tw)):
        ingest_handle("h", db_path=db, sequential=False)

    r = _day_row(db, "h", old, "getxapi")
    assert r["status"] == "mismatch"         # terminal — not reopened
    assert r["retry_count"] == 3


# ---------------------------------------------------------------------------
# Handle scoping
# ---------------------------------------------------------------------------

def test_pool_filter_scopes_to_one_handle(tmp_path):
    db = _fresh(tmp_path, "scope.db")
    today = datetime.date.today()
    prior = [(today - datetime.timedelta(days=n)).isoformat() for n in (5, 4, 3)]
    _seed_handle_with_history(db, "h1", prior)
    _seed_handle_with_history(db, "h2", prior)

    # Each handle has an eligible failed day (retry_count=0) at an old date.
    old = (today - datetime.timedelta(days=10)).isoformat()
    for h in ("h1", "h2"):
        for p in ("getxapi", "twitterapi"):
            _set_day(db, h, old, p, "failed", retry_count=0)

    gx = FakeSource({old: []}, "getxapi")
    tw = FakeSource({old: []}, "twitterapi")
    with patch("fintwit.tweet_sources.factory.get_source", side_effect=_get_source_factory(gx, tw)):
        ingest_handle("h1", db_path=db, sequential=False)

    # h1's failed day was claimed/processed; h2's is untouched (scoped dispatch).
    assert _day_row(db, "h1", old, "getxapi")["status"] != "failed"
    assert _day_row(db, "h2", old, "getxapi") == {"status": "failed", "retry_count": 0}


# ---------------------------------------------------------------------------
# ingest_all routing
# ---------------------------------------------------------------------------

def test_ingest_all_default_routes_to_pool(tmp_path, monkeypatch):
    db = _fresh(tmp_path, "rp.db")
    today = datetime.date.today()
    _seed_handle_with_history(db, "h", [(today - datetime.timedelta(days=n)).isoformat()
                                        for n in (5, 4, 3)])
    calls = []

    def fake_run_pool(handles, window, **kw):
        calls.append((list(handles), kw.get("handles_filter")))
        return {"by_status": {}}

    monkeypatch.setattr("fintwit.orchestration.runner.run_pool", fake_run_pool)
    monkeypatch.setattr("fintwit.orchestration.runner.reconcile_completed_days",
                        lambda conn: {"ok": 0, "mismatch": 0, "skipped": 0})
    ingest_all(db_path=db)

    assert calls, "run_pool was not called on the default path"
    assert calls[0] == (["h"], ["h"])        # scoped to the handle


def test_ingest_all_sequential_routes_to_legacy(tmp_path, monkeypatch):
    db = _fresh(tmp_path, "rs.db")
    today = datetime.date.today()
    _seed_handle_with_history(db, "h", [(today - datetime.timedelta(days=n)).isoformat()
                                        for n in (5, 4, 3)])
    pool_calls, seq_calls = [], []
    monkeypatch.setattr("fintwit.orchestration.runner.run_pool",
                        lambda *a, **k: pool_calls.append(1) or {"by_status": {}})
    monkeypatch.setattr("fintwit.orchestration.runner.delta_handle",
                        lambda *a, **k: seq_calls.append(1) or DayFetchSummary(handle="h"))
    ingest_all(db_path=db, sequential=True)

    assert seq_calls and not pool_calls


# ---------------------------------------------------------------------------
# ingest_all isolation (T7 regression, pool path)
# ---------------------------------------------------------------------------

def test_ingest_all_one_handle_failure_does_not_stop_batch(tmp_path):
    db = _fresh(tmp_path, "iso.db")
    today = datetime.date.today()
    t = today.isoformat()
    prior = [(today - datetime.timedelta(days=n)).isoformat() for n in (5, 4, 3)]
    for h in ("h_ok1", "h_bad", "h_ok2"):
        _seed_handle_with_history(db, h, prior)

    good = {t: [_tweet("a", f"{t}T10:00:00Z")]}

    class BadSource(FakeSource):
        def fetch_tweets(self, handle, start, end):
            if handle == "h_bad":
                raise RuntimeError("boom")
            return FetchResult(tweets=good.get(start.isoformat(), []), reached_floor=True)

    gx = BadSource(good, "getxapi")
    tw = BadSource(good, "twitterapi")
    with patch("fintwit.tweet_sources.factory.get_source", side_effect=_get_source_factory(gx, tw)):
        results = ingest_all(db_path=db)

    by = {r.handle: r.outcome for r in results}
    # Batch completed for everyone; the good handles are ok, the bad one is not.
    assert by["h_ok1"] == "ok"
    assert by["h_ok2"] == "ok"
    assert by["h_bad"] != "ok"               # pool absorbs the error into the ledger
