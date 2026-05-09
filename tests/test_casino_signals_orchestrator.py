from datetime import date, timedelta
from pathlib import Path

import pytest

from casino_dashboard.db.repository import get_signals, save_snapshot
from casino_dashboard.db.schema import init_db
from casino_dashboard.models import TickerSnapshot
from casino_dashboard.signals.orchestrator import compute_signals_for_ticker


def _snap(ticker: str, i: int, close: float = 100.0, volume: int = 1_000_000) -> TickerSnapshot:
    return TickerSnapshot(
        ticker=ticker,
        date=date(2024, 1, 1) + timedelta(days=i),
        open=close,
        high=close + 1,
        low=close - 1,
        close=close,
        adj_close=close,
        volume=volume,
        avg_volume_30d=None,
        news_items=[],
    )


def _populate_db(db: Path, ticker: str, n: int, close_fn=None, vol_fn=None) -> None:
    init_db(db)
    for i in range(n):
        close = close_fn(i) if close_fn else 100.0 + i
        vol = vol_fn(i) if vol_fn else 1_000_000
        save_snapshot(_snap(ticker, i, close=close, volume=vol), db)


def test_orchestrator_returns_all_expected_keys_with_full_history(tmp_path: Path):
    db = tmp_path / "test.db"
    _populate_db(db, "RKLB", 60)
    signals = compute_signals_for_ticker("RKLB", db)

    expected_keys = {
        "vol_ratio_30d",
        "return_1d",
        "return_5d",
        "return_20d",
        "dist_from_30d_high_pct",
        "dist_from_30d_low_pct",
        "near_breakout",
        "near_breakdown",
    }
    assert expected_keys.issubset(signals.keys())


def test_orchestrator_skips_signals_with_insufficient_history(tmp_path: Path):
    db = tmp_path / "test.db"
    # Only 3 days — not enough for 5d return, 20d return, 30d extremes, or vol_ratio
    _populate_db(db, "RKLB", 3)
    signals = compute_signals_for_ticker("RKLB", db)

    assert "return_20d" not in signals
    assert "return_5d" not in signals
    assert "dist_from_30d_high_pct" not in signals
    assert "vol_ratio_30d" not in signals


def test_near_breakout_flag_fires_near_high(tmp_path: Path):
    db = tmp_path / "test.db"
    # Flat history so latest close == 30d high → dist = 0.0 > -0.02 → near_breakout = 1.0
    _populate_db(db, "RKLB", 60, close_fn=lambda i: 100.0)
    signals = compute_signals_for_ticker("RKLB", db)
    assert signals.get("near_breakout") == pytest.approx(1.0)


def test_near_breakdown_flag_fires_near_low(tmp_path: Path):
    db = tmp_path / "test.db"
    # Flat history → latest close == 30d low → dist = 0.0 < 0.02 → near_breakdown = 1.0
    _populate_db(db, "RKLB", 60, close_fn=lambda i: 100.0)
    signals = compute_signals_for_ticker("RKLB", db)
    assert signals.get("near_breakdown") == pytest.approx(1.0)


def test_save_round_trip_via_repository(tmp_path: Path):
    db = tmp_path / "test.db"
    _populate_db(db, "RKLB", 60)
    signals = compute_signals_for_ticker("RKLB", db)

    today = date(2024, 1, 1) + timedelta(days=59)
    from casino_dashboard.db.repository import save_signal
    for name, value in signals.items():
        save_signal("RKLB", today, name, value, db)

    retrieved = get_signals("RKLB", today, db)
    for name, value in signals.items():
        assert name in retrieved
        assert retrieved[name] == pytest.approx(value)
