"""Tests for indicator helpers and the cache-aware fetcher.

Network-touching internals are monkeypatched. The build-an-indicator helper
is exercised against synthetic pandas Series so the math is checked without
hitting FRED or yfinance.
"""
from datetime import datetime, timezone

import pandas as pd
import pytest

from ticker_digest import cache
from ticker_digest.market import indicators
from ticker_digest.models import MarketIndicator


@pytest.fixture
def tmp_cache_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("TICKER_DIGEST_CACHE_DIR", str(tmp_path))
    return tmp_path


def _series(values: list[float], freq: str = "D") -> pd.Series:
    idx = pd.date_range(start="2001-01-01", periods=len(values), freq=freq)
    return pd.Series(values, index=idx, dtype=float)


def test_z_score_centers_on_mean():
    s = _series([1, 2, 3, 4, 5] * 100)
    # mean=3, std≈1.42 (population-ish via pandas)
    z = indicators._z_score(s, 5.0)
    assert z is not None
    assert 1.3 < z < 1.5


def test_z_score_returns_none_when_constant():
    s = _series([3.0] * 100)
    assert indicators._z_score(s, 3.0) is None


def test_z_score_returns_none_for_empty_series():
    assert indicators._z_score(pd.Series(dtype=float), 1.0) is None


def test_sparkline_truncates_to_60():
    s = _series(list(range(200)))
    spark = indicators._sparkline(s)
    assert len(spark) == 60
    last_key = max(spark)
    assert spark[last_key] == 199.0


def test_build_populates_value_and_z_and_history():
    s = _series([1, 2, 3, 4, 5] * 60)
    ind = indicators._build("Test", "TEST", "computed", "market", s)
    assert ind.value == 5.0
    assert ind.z_score is not None
    assert ind.error is None
    assert ind.bucket == "market"
    assert len(ind.history) == 60
    assert ind.as_of is not None


def test_build_returns_error_on_empty_series():
    ind = indicators._build("Test", "TEST", "fred", "economy", pd.Series(dtype=float))
    assert ind.value is None
    assert ind.error == "empty series"


def test_get_indicator_uses_cache(tmp_cache_dir, monkeypatch):
    cached = MarketIndicator(
        name="cached",
        series_id="UNRATE",
        source="fred",
        bucket="economy",
        value=4.2,
        z_score=0.1,
        as_of=datetime(2026, 4, 1, tzinfo=timezone.utc),
    )
    cache.set_indicator("UNRATE", cached, ttl_seconds=3600)

    def boom() -> MarketIndicator:
        raise AssertionError("fetcher should not be called when cache hits")

    monkeypatch.setitem(indicators.INDICATOR_REGISTRY, "UNRATE", indicators._Spec(boom))

    got = indicators.get_indicator("UNRATE")
    assert got.value == 4.2
    assert got.name == "cached"


def test_get_indicator_force_bypasses_cache(tmp_cache_dir, monkeypatch):
    cached = MarketIndicator(
        name="stale", series_id="UNRATE", source="fred", bucket="economy", value=99.0
    )
    cache.set_indicator("UNRATE", cached, ttl_seconds=3600)

    fresh = MarketIndicator(
        name="fresh", series_id="UNRATE", source="fred", bucket="economy", value=4.2
    )
    monkeypatch.setitem(
        indicators.INDICATOR_REGISTRY, "UNRATE", indicators._Spec(lambda: fresh)
    )

    got = indicators.get_indicator("UNRATE", force=True)
    assert got.name == "fresh" and got.value == 4.2


def test_errors_are_not_cached(tmp_cache_dir, monkeypatch):
    failed = MarketIndicator(
        name="x", series_id="UNRATE", source="fred", bucket="economy", error="boom"
    )
    monkeypatch.setitem(
        indicators.INDICATOR_REGISTRY, "UNRATE", indicators._Spec(lambda: failed)
    )
    indicators.get_indicator("UNRATE")
    assert cache.get_indicator("UNRATE") is None


def test_fetch_t10y2y_wraps_exceptions(monkeypatch):
    def boom(series_id, start=None):
        raise RuntimeError("FRED down")

    monkeypatch.setattr(indicators.fred_client, "fetch_series", boom)
    ind = indicators.fetch_t10y2y()
    assert ind.error and "FRED down" in ind.error
    assert ind.value is None


def test_fetch_unrate_happy_path(monkeypatch):
    fake = _series([3.5, 3.7, 3.9, 4.0, 4.1] * 60, freq="ME")

    def fake_fetch(series_id, start=None):
        assert series_id == "UNRATE"
        return fake

    monkeypatch.setattr(indicators.fred_client, "fetch_series", fake_fetch)
    ind = indicators.fetch_unrate()
    assert ind.error is None
    assert ind.value == pytest.approx(4.1)
    assert ind.z_score is not None
    assert ind.bucket == "economy"


def test_get_snapshot_collects_all_registry_entries(tmp_cache_dir, monkeypatch):
    def stub() -> MarketIndicator:
        return MarketIndicator(
            name="x", series_id="X", source="computed", bucket="market", value=1.0, z_score=0.0
        )

    stubs = {sid: indicators._Spec(stub) for sid in indicators.INDICATOR_REGISTRY}
    monkeypatch.setattr(indicators, "INDICATOR_REGISTRY", stubs)

    snapshot = indicators.get_snapshot()
    assert set(snapshot.indicators.keys()) == set(stubs.keys())
