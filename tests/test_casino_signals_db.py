import sqlite3
from datetime import date
from pathlib import Path

import pytest

from casino_dashboard.db.repository import get_latest_signals_all_tickers, get_signals, save_signal
from casino_dashboard.db.schema import init_db


def test_save_signal_idempotent(tmp_path: Path):
    db = tmp_path / "test.db"
    init_db(db)

    save_signal("RKLB", date(2024, 1, 1), "return_1d", 0.05, db)
    save_signal("RKLB", date(2024, 1, 1), "return_1d", 0.07, db)  # overwrite

    with sqlite3.connect(db) as conn:
        rows = conn.execute(
            "SELECT value FROM signals WHERE ticker='RKLB' AND date='2024-01-01' AND signal_name='return_1d'"
        ).fetchall()

    assert len(rows) == 1
    assert rows[0][0] == pytest.approx(0.07)


def test_get_latest_signals_all_tickers_shape(tmp_path: Path):
    db = tmp_path / "test.db"
    init_db(db)

    for ticker in ("RKLB", "IONQ", "SMR"):
        for signal in ("return_1d", "vol_ratio_30d"):
            save_signal(ticker, date(2024, 1, 1), signal, 1.0, db)

    df = get_latest_signals_all_tickers(db)
    assert set(df.index) == {"RKLB", "IONQ", "SMR"}
    assert "return_1d" in df.columns
    assert "vol_ratio_30d" in df.columns
    assert df.shape == (3, 2)


def test_get_latest_signals_all_tickers_empty_db(tmp_path: Path):
    db = tmp_path / "test.db"
    init_db(db)

    df = get_latest_signals_all_tickers(db)
    assert df.empty
