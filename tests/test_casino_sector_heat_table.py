"""Tests for the sector heat table rendering component."""
import math
from datetime import date

import pandas as pd
import pytest

from casino_dashboard.ui.components.colors import (
    tercile_bg_for_series,
    vol_exp_arrow,
)
from casino_dashboard.ui.components.sector_heat_table import (
    _fmt_days_since,
    _fmt_fraction,
    _fmt_pct,
    _fmt_usd_billions,
    build_sector_display_df,
)
from casino_dashboard.universe import Sector, Universe


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_universe_data(sectors: dict[str, list[str]]) -> dict:
    """Build universe_data dict with minimal Sector objects."""
    sector_objs = {}
    for sid, tickers in sectors.items():
        sector_objs[sid] = Sector(
            id=sid,
            display_name=sid.replace("_", " ").title(),
            description="",
            stage="mid",
            speculative=False,
            tickers=tickers,
        )
    return {"sectors": sector_objs, "ticker_to_sectors": {}}


def _make_heat_row(
    sector_id: str = "ai_infrastructure",
    etf_flow: float | None = 1.5,
    deal_total: float | None = 80_000_000_000.0,
    deal_count: int = 2,
    days_since: int | None = 7,
    social: float | None = 2.3,
    news_heat: float | None = 1.8,
    agg_return: float | None = 0.184,
    breadth: float | None = 0.875,
    atr_change: float | None = 0.02,
    n_tickers: int = 8,
) -> pd.DataFrame:
    data = {
        "etf_flow_5d_30d_ratio": [etf_flow],
        "deal_log_30d_total_usd": [deal_total],
        "deal_log_30d_count": [deal_count],
        "days_since_last_deal": [days_since],
        "agg_social_velocity": [social],
        "news_heat_ratio": [news_heat],
        "agg_return_30d": [agg_return],
        "pct_above_sma50": [breadth],
        "agg_atr_pct_change_30d": [atr_change],
        "constituent_count": [n_tickers],
    }
    return pd.DataFrame(data, index=[sector_id])


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

def test_fmt_pct_positive():
    assert _fmt_pct(0.184) == "+18.4%"


def test_fmt_pct_negative():
    assert _fmt_pct(-0.038) == "-3.8%"


def test_fmt_pct_none():
    assert _fmt_pct(None) == "—"


def test_fmt_pct_nan():
    assert _fmt_pct(float("nan")) == "—"


def test_fmt_fraction_75_percent():
    assert _fmt_fraction(0.75) == "75%"


def test_fmt_fraction_none():
    assert _fmt_fraction(None) == "—"


def test_fmt_usd_billions():
    assert _fmt_usd_billions(80_000_000_000.0) == "$80.0B"


def test_fmt_usd_millions():
    assert _fmt_usd_billions(1_200_000.0) == "$1M"


def test_fmt_usd_none():
    assert _fmt_usd_billions(None) == "—"


def test_fmt_days_since_recent():
    assert _fmt_days_since(2, "nuclear") == "2d ago"


def test_fmt_days_since_warn_threshold():
    result = _fmt_days_since(15, "nuclear")
    assert "⚠️" in result


def test_fmt_days_since_error_threshold():
    result = _fmt_days_since(31, "nuclear")
    assert "🔴" in result


def test_fmt_days_since_none():
    assert _fmt_days_since(None, "nuclear") == "—"


# ---------------------------------------------------------------------------
# vol_exp_arrow
# ---------------------------------------------------------------------------

def test_vol_exp_arrow_positive():
    assert vol_exp_arrow(0.01) == "↑"


def test_vol_exp_arrow_negative():
    assert vol_exp_arrow(-0.01) == "↓"


def test_vol_exp_arrow_flat():
    assert vol_exp_arrow(0.0) == "→"


def test_vol_exp_arrow_none():
    assert vol_exp_arrow(None) == "—"


def test_vol_exp_arrow_nan():
    assert vol_exp_arrow(float("nan")) == "—"


# ---------------------------------------------------------------------------
# tercile_bg_for_series
# ---------------------------------------------------------------------------

def test_tercile_top_gets_green():
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    colors = tercile_bg_for_series(s)
    assert "bbf7d0" in colors.iloc[-1]  # highest value → green


def test_tercile_bottom_gets_red():
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    colors = tercile_bg_for_series(s)
    assert "fecaca" in colors.iloc[0]  # lowest value → red


def test_tercile_nan_gets_empty_string():
    s = pd.Series([1.0, 2.0, float("nan"), 4.0, 5.0, 6.0])
    colors = tercile_bg_for_series(s)
    assert colors.iloc[2] == ""


def test_tercile_inverted_top_gets_green():
    """With invert=True, lower value = better = green (e.g. days_since_last_deal)."""
    s = pd.Series([1.0, 5.0, 10.0, 20.0, 30.0, 45.0])
    colors = tercile_bg_for_series(s, invert=True)
    assert "bbf7d0" in colors.iloc[0]  # lowest = most recent = green


def test_tercile_fewer_than_3_values_returns_empty():
    s = pd.Series([1.0, 2.0])
    colors = tercile_bg_for_series(s)
    assert all(c == "" for c in colors)


# ---------------------------------------------------------------------------
# build_sector_display_df
# ---------------------------------------------------------------------------

def test_build_display_df_basic_columns():
    universe = _make_universe_data({"ai_infrastructure": ["VRT", "ETN"]})
    heat = _make_heat_row("ai_infrastructure")
    display_df, numeric_df = build_sector_display_df(heat, universe)
    assert "ETF Flow" in display_df.columns
    assert "Mom 30d" in display_df.columns
    assert "Breadth" in display_df.columns
    assert "Vol Exp" in display_df.columns
    assert "Last Deal" in display_df.columns


def test_photonics_shows_na_for_etf_flow():
    """Photonics has no ETF — ETF Flow column must show 'n/a' not '—'."""
    universe = _make_universe_data({"photonics": ["AAOI", "POET"]})
    heat = _make_heat_row("photonics", etf_flow=None)
    display_df, numeric_df = build_sector_display_df(heat, universe)
    assert display_df.loc["Photonics", "ETF Flow"] == "n/a"
    assert numeric_df.loc["Photonics", "ETF Flow"] is None  # excluded from tercile


def test_sector_with_no_heat_data_renders_dashes(capsys):
    """Sectors with no data in the heat table render '—' cells, not crashes."""
    universe = _make_universe_data({"quantum": ["IONQ", "RGTI"]})
    empty_heat = pd.DataFrame()
    display_df, _ = build_sector_display_df(empty_heat, universe)
    # display_name is generated as sid.replace("_"," ").title() → "Quantum"
    assert display_df.loc["Quantum", "Mom 30d"] == "—"


def test_stale_deal_flag_in_display(capsys):
    """days_since_last_deal > 14 should produce warning symbol in Last Deal cell."""
    universe = _make_universe_data({"space": ["RKLB"]})
    heat = _make_heat_row("space", days_since=20)
    display_df, _ = build_sector_display_df(heat, universe)
    assert "⚠️" in display_df.loc["Space", "Last Deal"]


def test_critical_stale_flag_in_display():
    """days_since_last_deal > 30 should produce red flag in Last Deal cell."""
    universe = _make_universe_data({"space": ["RKLB"]})
    heat = _make_heat_row("space", days_since=45)
    display_df, _ = build_sector_display_df(heat, universe)
    assert "🔴" in display_df.loc["Space", "Last Deal"]


def test_sectors_sorted_alphabetically():
    universe = _make_universe_data({
        "quantum": ["IONQ"],
        "ai_infrastructure": ["VRT"],
        "nuclear": ["SMR"],
    })
    display_df, _ = build_sector_display_df(pd.DataFrame(), universe)
    # Index should be in alphabetical order of display names
    names = list(display_df.index)
    assert names == sorted(names)


def test_constituent_count_falls_back_to_universe_length():
    """When heat table is empty, constituent_count should use the universe ticker list length."""
    universe = _make_universe_data({"nuclear": ["SMR", "OKLO", "NNE", "BWXT", "NXE"]})
    display_df, numeric_df = build_sector_display_df(pd.DataFrame(), universe)
    assert numeric_df.loc["Nuclear", "# Tickers"] == 5.0


def test_all_eight_sectors_render_without_crash():
    """Full 8-sector universe with empty heat data must not raise."""
    sectors = {
        "nuclear": ["SMR", "OKLO"],
        "photonics": ["AAOI", "POET"],
        "quantum": ["IONQ", "RGTI"],
        "drones_defense": ["KTOS", "AVAV"],
        "space": ["RKLB", "ASTS"],
        "critical_minerals": ["MP"],
        "ai_infrastructure": ["VRT", "ETN"],
        "crypto_equities": ["COIN"],
    }
    universe = _make_universe_data(sectors)
    display_df, numeric_df = build_sector_display_df(pd.DataFrame(), universe)
    assert len(display_df) == 8
    assert not any(display_df["ETF Flow"].isna())  # no actual NaN — only "—" or "n/a" strings
