from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from casino_dashboard.db.repository import get_history, get_snapshot, save_snapshot
from casino_dashboard.db.schema import init_db
from casino_dashboard.models import NewsItem, TickerSnapshot


def _make_snap(ticker: str = "RKLB", snap_date: date = date(2024, 12, 31)) -> TickerSnapshot:
    return TickerSnapshot(
        ticker=ticker,
        date=snap_date,
        open=10.0,
        high=11.0,
        low=9.0,
        close=10.5,
        adj_close=10.3,
        volume=1_000_000,
        avg_volume_30d=950_000.0,
        news_items=[
            NewsItem(
                title="Test headline",
                link="https://example.com/1",
                publisher="TestPub",
                published_at=datetime(2024, 12, 31, 12, 0, tzinfo=timezone.utc),
            )
        ],
    )


def test_schema_creates_tables(tmp_path: Path):
    db = tmp_path / "test.db"
    init_db(db)
    import sqlite3
    with sqlite3.connect(db) as conn:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "ticker_snapshots" in tables
    assert "news_items" in tables


def test_schema_idempotent(tmp_path: Path):
    db = tmp_path / "test.db"
    init_db(db)
    init_db(db)  # calling twice must not raise


def test_save_and_get_snapshot_roundtrip(tmp_path: Path):
    db = tmp_path / "test.db"
    snap = _make_snap()
    save_snapshot(snap, db)

    retrieved = get_snapshot("RKLB", date(2024, 12, 31), db)
    assert retrieved is not None
    assert retrieved.ticker == "RKLB"
    assert retrieved.date == date(2024, 12, 31)
    assert retrieved.open == pytest.approx(10.0)
    assert retrieved.close == pytest.approx(10.5)
    assert retrieved.adj_close == pytest.approx(10.3)
    assert retrieved.volume == 1_000_000
    assert retrieved.avg_volume_30d == pytest.approx(950_000.0)
    assert len(retrieved.news_items) == 1
    assert retrieved.news_items[0].title == "Test headline"


def test_get_snapshot_missing_returns_none(tmp_path: Path):
    db = tmp_path / "test.db"
    init_db(db)
    result = get_snapshot("NONEXISTENT", date(2024, 1, 1), db)
    assert result is None


def test_save_snapshot_overwrites_on_conflict(tmp_path: Path):
    db = tmp_path / "test.db"
    snap = _make_snap()
    save_snapshot(snap, db)

    updated = snap.model_copy(update={"close": 99.0})
    save_snapshot(updated, db)

    retrieved = get_snapshot("RKLB", date(2024, 12, 31), db)
    assert retrieved is not None
    assert retrieved.close == pytest.approx(99.0)


def test_save_snapshot_null_avg_volume(tmp_path: Path):
    db = tmp_path / "test.db"
    snap = _make_snap().model_copy(update={"avg_volume_30d": None})
    save_snapshot(snap, db)

    retrieved = get_snapshot("RKLB", date(2024, 12, 31), db)
    assert retrieved is not None
    assert retrieved.avg_volume_30d is None


def test_get_history_returns_ordered_results(tmp_path: Path):
    db = tmp_path / "test.db"
    dates = [date(2024, 12, d) for d in range(29, 20, -1)]  # 29, 28, ... 21
    for d in dates:
        save_snapshot(_make_snap(snap_date=d), db)

    history = get_history("RKLB", 5, db)
    assert len(history) == 5
    # Should be most-recent first (ORDER BY date DESC)
    result_dates = [s.date for s in history]
    assert result_dates == sorted(result_dates, reverse=True)


def test_get_history_empty_for_unknown_ticker(tmp_path: Path):
    db = tmp_path / "test.db"
    init_db(db)
    history = get_history("UNKNWN", 10, db)
    assert history == []


def test_multiple_tickers_isolated(tmp_path: Path):
    db = tmp_path / "test.db"
    save_snapshot(_make_snap("RKLB"), db)
    save_snapshot(_make_snap("NVDA"), db)

    rklb = get_snapshot("RKLB", date(2024, 12, 31), db)
    nvda = get_snapshot("NVDA", date(2024, 12, 31), db)
    assert rklb is not None and rklb.ticker == "RKLB"
    assert nvda is not None and nvda.ticker == "NVDA"


def test_save_snapshot_idempotent_same_ticker_date(tmp_path: Path):
    import sqlite3
    db = tmp_path / "test.db"
    snap = _make_snap()
    save_snapshot(snap, db)

    updated = snap.model_copy(update={"close": 77.0})
    save_snapshot(updated, db)

    with sqlite3.connect(db) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM ticker_snapshots WHERE ticker = ? AND date = ?",
            ("RKLB", "2024-12-31"),
        ).fetchone()[0]
    assert count == 1

    retrieved = get_snapshot("RKLB", date(2024, 12, 31), db)
    assert retrieved is not None
    assert retrieved.close == pytest.approx(77.0)


def test_news_items_dedup_by_ticker_link(tmp_path: Path):
    import sqlite3
    db = tmp_path / "test.db"
    snap = _make_snap()
    save_snapshot(snap, db)
    # Save same snapshot again — same (ticker, link) should not create a second row
    save_snapshot(snap, db)

    with sqlite3.connect(db) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM news_items WHERE ticker = ? AND link = ?",
            ("RKLB", "https://example.com/1"),
        ).fetchone()[0]
    assert count == 1
