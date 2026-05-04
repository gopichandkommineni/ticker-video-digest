"""Tests for social_mentions repository methods."""
import tempfile
from datetime import date
from pathlib import Path

import pytest

from casino_dashboard.db.repository import (
    get_latest_social_mentions,
    get_social_history,
    save_social_mention,
)
from casino_dashboard.db.schema import init_db


@pytest.fixture
def db(tmp_path: Path) -> Path:
    path = tmp_path / "test.db"
    init_db(path)
    return path


def test_save_social_mention_idempotent(db: Path):
    d = date(2026, 5, 4)
    save_social_mention("AAOI", d, "apewisdom", 100, 50, 200, db_path=db)
    save_social_mention("AAOI", d, "apewisdom", 100, 50, 200, db_path=db)  # duplicate
    hist = get_social_history("AAOI", "apewisdom", 10, db)
    assert len(hist) == 1


def test_get_social_history_returns_expected_shape(db: Path):
    save_social_mention("AAOI", date(2026, 5, 3), "apewisdom", 80, 40, 160, db_path=db)
    save_social_mention("AAOI", date(2026, 5, 4), "apewisdom", 100, 50, 200, db_path=db)
    hist = get_social_history("AAOI", "apewisdom", 30, db)
    assert list(hist.columns) == ["date", "mention_count", "mentions_24h_ago"]
    assert len(hist) == 2
    # Newest first
    assert hist.iloc[0]["mention_count"] == 100


def test_get_latest_social_mentions_one_row_per_ticker(db: Path):
    # Two tickers, two dates — only latest per ticker returned
    save_social_mention("AAOI", date(2026, 5, 3), "apewisdom", 80, 40, 160, db_path=db)
    save_social_mention("AAOI", date(2026, 5, 4), "apewisdom", 100, 50, 200, db_path=db)
    save_social_mention("RKLB", date(2026, 5, 4), "apewisdom", 60, 30, 120, db_path=db)
    df = get_latest_social_mentions(db)
    assert "AAOI" in df.index
    assert "RKLB" in df.index
    assert len(df) == 2
    assert df.loc["AAOI", "latest_mention_count"] == 100


def test_empty_db_returns_empty_dataframe(db: Path):
    df = get_latest_social_mentions(db)
    assert df.empty
    hist = get_social_history("AAOI", "apewisdom", 10, db)
    assert hist.empty
