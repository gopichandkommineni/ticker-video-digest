"""Tests for casino_dashboard.ui.sector_aggregator."""
import math

import pandas as pd
import pytest

from casino_dashboard.ui.sector_aggregator import (
    aggregate_signals_by_sector,
    classify_sector_health,
)
from casino_dashboard.universe import Sector, Universe


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_universe(*sector_specs: tuple[str, list[str]]) -> Universe:
    """Build a minimal Universe from (sector_id, [tickers]) pairs."""
    sectors: dict[str, Sector] = {}
    for sector_id, tickers in sector_specs:
        sectors[sector_id] = Sector(
            id=sector_id,
            display_name=sector_id.capitalize(),
            description="test",
            stage="mid",
            speculative=False,
            tickers=tickers,
        )
    return Universe(sectors=sectors)


def _make_signals(rows: dict[str, dict]) -> pd.DataFrame:
    """Build a signals DataFrame indexed by ticker."""
    return pd.DataFrame.from_dict(rows, orient="index")


# ── aggregate_signals_by_sector tests ────────────────────────────────────────

def test_aggregate_single_sector_averages():
    """Three tickers in one sector → correct column averages."""
    signals = _make_signals(
        {
            "AAA": {"return_1d": 0.01, "return_5d": 0.06, "return_20d": 0.10,
                    "near_breakout": 1.0, "near_breakdown": 0.0,
                    "vol_ratio_30d": 1.5, "apewisdom_velocity_24h": 2.0},
            "BBB": {"return_1d": 0.02, "return_5d": 0.08, "return_20d": 0.12,
                    "near_breakout": 1.0, "near_breakdown": 0.0,
                    "vol_ratio_30d": 1.0, "apewisdom_velocity_24h": 3.0},
            "CCC": {"return_1d": 0.03, "return_5d": 0.10, "return_20d": 0.14,
                    "near_breakout": 0.0, "near_breakdown": 0.0,
                    "vol_ratio_30d": 2.0, "apewisdom_velocity_24h": 1.0},
        }
    )
    universe = _make_universe(("alpha", ["AAA", "BBB", "CCC"]))
    result = aggregate_signals_by_sector(signals, universe)

    assert "alpha" in result.index
    row = result.loc["alpha"]

    assert row["n_tickers"] == 3
    assert row["avg_return_1d"] == pytest.approx(0.02)
    assert row["avg_return_5d"] == pytest.approx(0.08)
    assert row["avg_return_20d"] == pytest.approx(0.12)
    assert row["avg_vol_ratio"] == pytest.approx(1.5)
    assert row["avg_apewisdom_velocity"] == pytest.approx(2.0)
    # 2 of 3 tickers have near_breakout > 0 → 66.7%
    assert row["pct_near_breakout"] == pytest.approx(2 / 3)
    # 0 of 3 have near_breakdown → 0%
    assert row["pct_near_breakdown"] == pytest.approx(0.0)


def test_aggregate_multi_sector_ticker_counted_in_both():
    """RKLB-style ticker in two sectors contributes to both aggregates."""
    signals = _make_signals(
        {
            "RKLB": {"return_5d": 0.07, "return_1d": 0.01, "return_20d": 0.05,
                     "near_breakout": 1.0, "near_breakdown": 0.0,
                     "vol_ratio_30d": 1.8, "apewisdom_velocity_24h": float("nan")},
            "SOLO": {"return_5d": 0.02, "return_1d": 0.00, "return_20d": 0.01,
                     "near_breakout": 0.0, "near_breakdown": 0.0,
                     "vol_ratio_30d": 1.0, "apewisdom_velocity_24h": float("nan")},
        }
    )
    universe = _make_universe(
        ("space", ["RKLB", "SOLO"]),
        ("defense", ["RKLB"]),
    )
    result = aggregate_signals_by_sector(signals, universe)

    # RKLB contributes to both sectors
    assert "space" in result.index
    assert "defense" in result.index

    space_row = result.loc["space"]
    defense_row = result.loc["defense"]

    # Space: average of RKLB (0.07) and SOLO (0.02) = 0.045
    assert space_row["avg_return_5d"] == pytest.approx(0.045)
    # Defense: only RKLB = 0.07
    assert defense_row["avg_return_5d"] == pytest.approx(0.07)

    # n_tickers reflects universe membership, not signal presence
    assert space_row["n_tickers"] == 2
    assert defense_row["n_tickers"] == 1


def test_aggregate_nan_apewisdom_ignored_in_mean():
    """NaN apewisdom_velocity values are ignored; mean is over valid tickers only."""
    signals = _make_signals(
        {
            "X": {"return_5d": 0.01, "return_1d": 0.0, "return_20d": 0.0,
                  "near_breakout": 0.0, "near_breakdown": 0.0,
                  "vol_ratio_30d": 1.0, "apewisdom_velocity_24h": 3.0},
            "Y": {"return_5d": 0.01, "return_1d": 0.0, "return_20d": 0.0,
                  "near_breakout": 0.0, "near_breakdown": 0.0,
                  "vol_ratio_30d": 1.0, "apewisdom_velocity_24h": float("nan")},
            "Z": {"return_5d": 0.01, "return_1d": 0.0, "return_20d": 0.0,
                  "near_breakout": 0.0, "near_breakdown": 0.0,
                  "vol_ratio_30d": 1.0, "apewisdom_velocity_24h": float("nan")},
        }
    )
    universe = _make_universe(("nano", ["X", "Y", "Z"]))
    result = aggregate_signals_by_sector(signals, universe)

    row = result.loc["nano"]
    # Only X has a valid velocity; Y and Z are NaN → mean should be 3.0
    assert row["avg_apewisdom_velocity"] == pytest.approx(3.0)


def test_aggregate_all_nan_apewisdom_returns_none():
    """If all tickers in a sector have NaN apewisdom, avg is None."""
    signals = _make_signals(
        {
            "P": {"return_5d": 0.01, "apewisdom_velocity_24h": float("nan")},
            "Q": {"return_5d": 0.02, "apewisdom_velocity_24h": float("nan")},
        }
    )
    universe = _make_universe(("sector_a", ["P", "Q"]))
    result = aggregate_signals_by_sector(signals, universe)

    row = result.loc["sector_a"]
    assert row["avg_apewisdom_velocity"] is None


def test_aggregate_empty_signals_returns_empty_df():
    """Empty signals_df → empty result DataFrame, no crash."""
    signals = pd.DataFrame()
    universe = _make_universe(("alpha", ["AAA", "BBB"]))
    result = aggregate_signals_by_sector(signals, universe)
    assert isinstance(result, pd.DataFrame)
    assert result.empty


def test_aggregate_sector_health_column_present():
    """sector_health column exists and contains valid labels."""
    signals = _make_signals(
        {
            "AAA": {"return_5d": 0.08, "return_1d": 0.01, "return_20d": 0.05,
                    "near_breakout": 1.0, "near_breakdown": 0.0,
                    "vol_ratio_30d": 1.5, "apewisdom_velocity_24h": 2.0},
        }
    )
    universe = _make_universe(("alpha", ["AAA"]))
    result = aggregate_signals_by_sector(signals, universe)

    assert "sector_health" in result.columns
    assert result.loc["alpha", "sector_health"] in ("hot", "cold", "mixed", "quiet")


# ── classify_sector_health tests ─────────────────────────────────────────────

def test_classify_sector_health_hot():
    """avg_return_5d > 5% AND pct_near_breakout > 30% → hot."""
    row = pd.Series(
        {"avg_return_5d": 0.08, "pct_near_breakout": 0.40, "pct_near_breakdown": 0.05}
    )
    assert classify_sector_health(row) == "hot"


def test_classify_sector_health_cold():
    """avg_return_5d < -5% AND pct_near_breakdown > 30% → cold."""
    row = pd.Series(
        {"avg_return_5d": -0.07, "pct_near_breakout": 0.0, "pct_near_breakdown": 0.40}
    )
    assert classify_sector_health(row) == "cold"


def test_classify_sector_health_mixed():
    """Both pct_near_breakout and pct_near_breakdown > 20% → mixed (divergent sector)."""
    row = pd.Series(
        {"avg_return_5d": 0.01, "pct_near_breakout": 0.35, "pct_near_breakdown": 0.35}
    )
    assert classify_sector_health(row) == "mixed"


def test_classify_sector_health_quiet():
    """Moderate values that meet no threshold → quiet."""
    row = pd.Series(
        {"avg_return_5d": 0.02, "pct_near_breakout": 0.10, "pct_near_breakdown": 0.05}
    )
    assert classify_sector_health(row) == "quiet"


def test_classify_sector_health_nan_values_fall_through_to_quiet():
    """NaN values do not satisfy any threshold → quiet."""
    row = pd.Series(
        {
            "avg_return_5d": float("nan"),
            "pct_near_breakout": float("nan"),
            "pct_near_breakdown": float("nan"),
        }
    )
    assert classify_sector_health(row) == "quiet"


def test_classify_sector_health_hot_boundary_not_met():
    """avg_return_5d exactly at threshold (not strictly greater) → not hot."""
    row = pd.Series(
        {"avg_return_5d": 0.05, "pct_near_breakout": 0.31, "pct_near_breakdown": 0.0}
    )
    # 0.05 is NOT > 0.05, so hot is not triggered
    result = classify_sector_health(row)
    assert result != "hot"


def test_classify_sector_health_hot_takes_priority_over_mixed():
    """When hot criteria met and both breakout/breakdown > 20%, hot wins (checked first)."""
    row = pd.Series(
        {"avg_return_5d": 0.09, "pct_near_breakout": 0.45, "pct_near_breakdown": 0.25}
    )
    assert classify_sector_health(row) == "hot"
