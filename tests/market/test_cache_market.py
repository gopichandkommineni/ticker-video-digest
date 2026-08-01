"""Tests for the market_indicators and market_thesis cache tables."""
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from core import cache
from core.models import MarketIndicator, MarketThesis


@pytest.fixture
def tmp_cache_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("TICKER_DIGEST_CACHE_DIR", str(tmp_path))
    return tmp_path


def _ind() -> MarketIndicator:
    return MarketIndicator(
        name="Unemployment",
        series_id="UNRATE",
        source="fred",
        bucket="economy",
        value=4.1,
        z_score=0.3,
        as_of=datetime(2026, 4, 1, tzinfo=timezone.utc),
        history={"2026-03-01": 4.0, "2026-04-01": 4.1},
    )


def _thesis() -> MarketThesis:
    return MarketThesis(
        narrative="n",
        bull_case=["a"],
        bear_case=["b"],
        key_watch_items=["c"],
        regime="neutral",
        generated_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
    )


def test_indicator_roundtrip(tmp_cache_dir):
    cache.set_indicator("UNRATE", _ind(), ttl_seconds=3600)
    got = cache.get_indicator("UNRATE")
    assert got is not None
    assert got.value == 4.1
    assert got.history == {"2026-03-01": 4.0, "2026-04-01": 4.1}


def test_indicator_per_row_ttl_expiry(tmp_cache_dir):
    cache.set_indicator("UNRATE", _ind(), ttl_seconds=60)
    db = tmp_cache_dir / "cache.db"
    conn = sqlite3.connect(db)
    old = (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat()
    conn.execute("UPDATE market_indicators SET cached_at = ? WHERE series_id = ?", (old, "UNRATE"))
    conn.commit()
    conn.close()
    assert cache.get_indicator("UNRATE") is None


def test_indicator_overwrites(tmp_cache_dir):
    cache.set_indicator("UNRATE", _ind(), ttl_seconds=60)
    new = _ind().model_copy(update={"value": 5.0})
    cache.set_indicator("UNRATE", new, ttl_seconds=60)
    assert cache.get_indicator("UNRATE").value == 5.0


def test_indicator_missing_returns_none(tmp_cache_dir):
    assert cache.get_indicator("XYZ") is None


def test_thesis_roundtrip(tmp_cache_dir):
    cache.set_thesis("h1", _thesis())
    got = cache.get_thesis("h1")
    assert got is not None
    assert got.regime == "neutral"


def test_thesis_ttl_expiry(tmp_cache_dir):
    cache.set_thesis("h1", _thesis())
    db = tmp_cache_dir / "cache.db"
    conn = sqlite3.connect(db)
    old = (datetime.now(timezone.utc) - timedelta(hours=7)).isoformat()
    conn.execute("UPDATE market_thesis SET cached_at = ? WHERE snapshot_hash = ?", (old, "h1"))
    conn.commit()
    conn.close()
    assert cache.get_thesis("h1") is None
