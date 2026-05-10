"""Sector heat ranking table component (spec §4).

Renders the multi-column sector ranking table with:
  - Three dimension groups: Capital Flows, Hype, Growth
  - Per-column tercile color coding (green/yellow/red), NOT per-row
  - "n/a" for sectors with no ETF (Photonics)
  - Stale-data warning flags for deal log (>14d yellow, >30d red)
  - Sortable via st.dataframe
"""
from __future__ import annotations

import math
from datetime import date

import pandas as pd
import streamlit as st

from casino_dashboard.ui.components.colors import tercile_bg_for_series, vol_exp_arrow

# Columns that should be inverted for tercile coloring (lower = better)
_INVERT_COLS = {"days_since_last_deal"}

# Columns excluded from tercile coloring (categorical, string-only)
_NO_TERCILE_COLS = {"vol_exp"}

_ETF_NO_DATA_SECTORS = {"photonics"}

_STALE_WARN_DAYS = 14
_STALE_ERROR_DAYS = 30


def _fmt_pct(v: float | None, decimals: int = 1) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    sign = "+" if v >= 0 else ""
    return f"{sign}{v * 100:.{decimals}f}%"


def _fmt_multiplier(v: float | None, decimals: int = 1) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    return f"{v:.{decimals}f}×"


def _fmt_usd_billions(v: float | None) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    b = v / 1_000_000_000
    if b >= 1:
        return f"${b:.1f}B"
    m = v / 1_000_000
    if m >= 1:
        return f"${m:.0f}M"
    return f"${v:,.0f}"


def _fmt_days_since(days: int | None, sector: str) -> str:
    if days is None:
        return "—"
    suffix = ""
    if days > _STALE_ERROR_DAYS:
        suffix = " 🔴"
    elif days > _STALE_WARN_DAYS:
        suffix = " ⚠️"
    return f"{days}d ago{suffix}"


def _fmt_fraction(v: float | None) -> str:
    """Format a 0–1 fraction as a percentage, e.g. 0.625 → '62.5%'."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    return f"{v * 100:.0f}%"


def build_sector_display_df(
    heat_df: pd.DataFrame,
    universe_data: dict,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build display and numeric DataFrames for the sector ranking table.

    Returns:
        display_df: formatted strings, indexed by sector display_name
        numeric_df: raw float values (same index/columns), for tercile coloring
    """
    sectors = universe_data.get("sectors", {})

    display_rows = []
    numeric_rows = []

    sector_order = sorted(sectors.keys())

    for sector_id in sector_order:
        sector = sectors[sector_id]
        display_name = sector.display_name

        if not heat_df.empty and sector_id in heat_df.index:
            row = heat_df.loc[sector_id]
        else:
            row = pd.Series(dtype=object)

        def _get(col: str) -> float | None:
            v = row.get(col) if len(row) > 0 else None
            if v is None:
                return None
            try:
                f = float(v)
                return None if math.isnan(f) else f
            except (TypeError, ValueError):
                return None

        etf_flow = _get("etf_flow_5d_30d_ratio")
        deal_total = _get("deal_log_30d_total_usd")
        deal_count_raw = row.get("deal_log_30d_count") if len(row) > 0 else None
        days_since_raw = row.get("days_since_last_deal") if len(row) > 0 else None
        social = _get("agg_social_velocity")
        news_heat = _get("news_heat_ratio")
        agg_return = _get("agg_return_30d")
        breadth = _get("pct_above_sma50")
        atr_change = _get("agg_atr_pct_change_30d")
        n_tickers = int(row.get("constituent_count", len(sector.tickers))) if len(row) > 0 else len(sector.tickers)

        try:
            days_since = int(days_since_raw) if days_since_raw is not None else None
        except (TypeError, ValueError):
            days_since = None

        # "n/a" for sectors with no ETF
        if sector_id in _ETF_NO_DATA_SECTORS:
            etf_flow_display = "n/a"
            etf_flow_num = None
        else:
            etf_flow_display = _fmt_multiplier(etf_flow) if etf_flow is not None else "—"
            etf_flow_num = etf_flow

        display_rows.append({
            "Sector": display_name,
            "ETF Flow": etf_flow_display,
            "Deals 30d": _fmt_usd_billions(deal_total),
            "Social": _fmt_multiplier(social),
            "News Heat": _fmt_multiplier(news_heat),
            "Mom 30d": _fmt_pct(agg_return),
            "Breadth": _fmt_fraction(breadth),
            "Vol Exp": vol_exp_arrow(atr_change),
            "# Tickers": n_tickers,
            "Last Deal": _fmt_days_since(days_since, sector_id),
        })

        numeric_rows.append({
            "Sector": display_name,
            "ETF Flow": etf_flow_num,
            "Deals 30d": deal_total,
            "Social": social,
            "News Heat": news_heat,
            "Mom 30d": agg_return,
            "Breadth": breadth,
            "Vol Exp": None,  # excluded from tercile
            "# Tickers": float(n_tickers),
            "Last Deal": float(days_since) if days_since is not None else None,
        })

    display_df = pd.DataFrame(display_rows).set_index("Sector")
    numeric_df = pd.DataFrame(numeric_rows).set_index("Sector")
    return display_df, numeric_df


def _apply_tercile_styles(display_df: pd.DataFrame, numeric_df: pd.DataFrame) -> pd.io.formats.style.Styler:
    """Apply per-column tercile background colors to the display DataFrame."""
    styler = display_df.style

    tercile_cols = [c for c in display_df.columns if c not in _NO_TERCILE_COLS and c != "# Tickers"]

    for col in tercile_cols:
        if col not in numeric_df.columns:
            continue
        invert = col in _INVERT_COLS
        numeric_series = numeric_df[col]

        style_series = tercile_bg_for_series(numeric_series, invert=invert)

        def _make_applier(s: pd.Series):
            def _apply_col(x: pd.Series) -> list[str]:
                return [s.get(idx, "") for idx in x.index]
            return _apply_col

        styler = styler.apply(_make_applier(style_series), subset=[col], axis=0)

    return styler


def render_sector_heat_table(
    heat_df: pd.DataFrame,
    universe_data: dict,
) -> str | None:
    """Render the sector ranking table and return the selected sector_id.

    Args:
        heat_df: DataFrame from load_sector_heat() — may be empty on first run
        universe_data: dict from load_universe_for_ui()

    Returns:
        sector_id of the user-selected sector, or None if no selection.
    """
    sectors = universe_data.get("sectors", {})
    if not sectors:
        st.warning("No sectors found in universe configuration.")
        return None

    if heat_df.empty:
        st.info(
            "Sector heat data not yet available. The daily refresh will populate this "
            "table on its next run (scheduled 13:00 UTC). Check back after the next refresh."
        )
        # Still show the structure with blank data so the user knows what's coming
        heat_df = pd.DataFrame()

    # Dimension header
    st.markdown(
        """
        <div style="display:flex; gap:24px; margin-bottom:4px; font-size:0.85rem; font-weight:600;">
            <span style="color:#2563eb;">◼ Capital Flows</span>
            &nbsp;&nbsp;&nbsp;
            <span style="color:#9333ea;">◼ Hype</span>
            &nbsp;&nbsp;&nbsp;
            <span style="color:#16a34a;">◼ Growth</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    display_df, numeric_df = build_sector_display_df(heat_df, universe_data)

    try:
        styled = _apply_tercile_styles(display_df, numeric_df)
        st.dataframe(
            styled,
            width="stretch",
            height=320,
        )
    except Exception:
        # Fallback: unstyled table if Styler fails (e.g., older Streamlit)
        st.dataframe(display_df, width="stretch", height=320)

    # Sector selector for drill-down
    sector_display_names = {
        s.display_name: sid for sid, s in sectors.items()
    }
    selected_display = st.selectbox(
        "Drill into sector →",
        options=["(none)"] + sorted(sector_display_names.keys()),
        index=0,
        key="sector_heat_selector",
    )
    if selected_display == "(none)":
        return None
    return sector_display_names.get(selected_display)


def render_constituent_table(
    constituents_df: pd.DataFrame,
    sector_display_name: str,
) -> None:
    """Render the in-sector constituent ranking table.

    constituents_df: indexed by ticker, columns from load_sector_constituents_ranking.
    """
    st.subheader(f"{sector_display_name} — constituent breakdown")

    if constituents_df.empty:
        st.info("No constituent data available for this sector.")
        return

    display_rows = []
    for ticker, row in constituents_df.iterrows():
        def _sig(col: str) -> float | None:
            v = row.get(col)
            if v is None:
                return None
            try:
                f = float(v)
                return None if math.isnan(f) else f
            except (TypeError, ValueError):
                return None

        nb = _sig("near_breakout")
        nd = _sig("near_breakdown")
        if nb and nb > 0:
            setup = "BREAKOUT"
        elif nd and nd > 0:
            setup = "BREAKDOWN"
        else:
            setup = "NEUTRAL"

        above_sma = _sig("pct_above_sma50")
        breadth_display = "✓ Above" if above_sma == 1.0 else ("✗ Below" if above_sma == 0.0 else "—")

        news_7d = int(row.get("news_7d_count", 0) or 0)

        display_rows.append({
            "Ticker": ticker,
            "Mom 30d": _fmt_pct(_sig("return_1m")),
            "SMA50": breadth_display,
            "Setup": setup,
            "Social": _fmt_multiplier(_sig("apewisdom_velocity_24h")),
            "News 7d": news_7d if news_7d > 0 else "—",
        })

    display_df = pd.DataFrame(display_rows).set_index("Ticker")

    def _setup_style(v: str) -> str:
        if v == "BREAKOUT":
            return "color: #16a34a; font-weight: 600"
        if v == "BREAKDOWN":
            return "color: #dc2626; font-weight: 600"
        return "color: #6b7280"

    def _mom_style(v: str) -> str:
        if v.startswith("+"):
            return "color: #16a34a"
        if v.startswith("-"):
            return "color: #dc2626"
        return ""

    try:
        styled = (
            display_df.style
            .map(_setup_style, subset=["Setup"])
            .map(_mom_style, subset=["Mom 30d"])
        )
        event = st.dataframe(
            styled,
            width="stretch",
            on_select="rerun",
            selection_mode="single-row",
        )
    except Exception:
        event = st.dataframe(
            display_df,
            width="stretch",
            on_select="rerun",
            selection_mode="single-row",
        )

    # Navigate to the ticker detail page when a row is selected
    selected_rows = (event.selection.get("rows") or []) if hasattr(event, "selection") else []
    if selected_rows:
        selected_ticker = display_df.index[selected_rows[0]]
        st.page_link(
            "pages/02_Ticker_Detail.py",
            label=f"Open {selected_ticker} detail page →",
            icon="📈",
        )

    st.caption(
        "Select a row to open the ticker detail page. "
        "SMA50 = whether the stock is currently above its 50-day moving average."
    )
