"""Tests for ticker_metadata and manual_notes repository methods."""
from datetime import date

import pandas as pd
import pytest

from casino_dashboard.data.yfinance_metadata import TickerMetadata
from casino_dashboard.db.repository import (
    get_latest_metadata_all_tickers,
    get_manual_notes_all_tickers,
    save_manual_note,
    save_ticker_metadata,
)
from casino_dashboard.db.schema import init_db


def _sample_metadata(ticker: str = "AAOI") -> TickerMetadata:
    return TickerMetadata(
        ticker=ticker,
        fifty_two_week_high=190.0,
        fifty_two_week_low=12.5,
        short_pct_of_float=0.135,
        short_ratio_days=0.95,
        analyst_target_mean=111.75,
        held_pct_insiders=0.0479,
        held_pct_institutions=0.6428,
        market_cap=13_970_000_000,
        revenue_ttm=455_710_000,
        revenue_growth_yoy=0.8275,
        profit_margin=-0.0839,
        beta=3.76,
        next_earnings_date=date(2026, 5, 7),
        next_earnings_time="AMC",
        last_earnings_date=date(2026, 2, 5),
    )


# ── Test 1: save_ticker_metadata is idempotent ────────────────────────────────

def test_save_ticker_metadata_idempotent(tmp_path):
    db = tmp_path / "test.db"
    init_db(db)
    meta = _sample_metadata()

    save_ticker_metadata(meta, db)
    save_ticker_metadata(meta, db)  # second save should not raise or duplicate

    df = get_latest_metadata_all_tickers(db)
    assert len(df) == 1
    assert df.index[0] == "AAOI"


# ── Test 2: get_latest_metadata_all_tickers returns expected shape ────────────

def test_get_latest_metadata_all_tickers_shape(tmp_path):
    db = tmp_path / "test.db"
    init_db(db)

    for ticker in ["AAOI", "POET", "IONQ"]:
        save_ticker_metadata(_sample_metadata(ticker), db)

    df = get_latest_metadata_all_tickers(db)
    assert set(df.index) == {"AAOI", "POET", "IONQ"}
    assert "fifty_two_week_high" in df.columns
    assert "beta" in df.columns
    assert "next_earnings_date" in df.columns


# ── Test 3: manual note save and retrieve roundtrip ───────────────────────────

def test_manual_note_save_and_retrieve(tmp_path):
    db = tmp_path / "test.db"
    init_db(db)

    save_manual_note("AAOI", "Texas grant", None, db)
    save_manual_note("POET", None, "Marvell NDA cancellation", db)

    df = get_manual_notes_all_tickers(db)
    assert df.loc["AAOI", "catalyst"] == "Texas grant"
    assert pd.isna(df.loc["AAOI", "red_flag"])
    assert pd.isna(df.loc["POET", "catalyst"])
    assert df.loc["POET", "red_flag"] == "Marvell NDA cancellation"


# ── Test 4: empty DB returns empty DataFrame ──────────────────────────────────

def test_empty_db_returns_empty_dataframe(tmp_path):
    db = tmp_path / "test.db"
    init_db(db)

    meta_df = get_latest_metadata_all_tickers(db)
    notes_df = get_manual_notes_all_tickers(db)

    assert meta_df.empty
    assert notes_df.empty
