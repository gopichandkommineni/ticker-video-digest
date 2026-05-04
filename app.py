"""Casino-Coherent Momentum Dashboard — Sectors Overview (root page)."""
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Casino Dashboard", layout="wide")

from casino_dashboard.ui.loaders import (  # noqa: E402
    load_sector_aggregates,
    load_signals_matrix,
    load_universe_for_ui,
)
from casino_dashboard.ui.sector_aggregator import health_label  # noqa: E402
from casino_dashboard.ui.sector_card import sector_card  # noqa: E402
from casino_dashboard.ui.formatting import format_pct, format_ratio  # noqa: E402

st.title("Casino-Coherent Momentum Dashboard")
st.caption(
    "Daily refreshed signals across 8 narrative themes. "
    "Read STRATEGY.md for thesis. Not investment advice."
)

# ── Sector Pulse heatmap ──────────────────────────────────────────────────────
st.subheader("Sector Pulse")
st.caption("Live aggregates across the 54-ticker universe")

agg_df = load_sector_aggregates()

if not agg_df.empty:
    def _fmt_vel(x: float | None) -> str:
        if x is None or (isinstance(x, float) and pd.isna(x)):
            return "—"
        return f"{x:.1f}x"

    display_agg = pd.DataFrame(
        {
            "Sector": agg_df["display_name"],
            "# Tickers": agg_df["n_tickers"].astype(int),
            "Avg 1d": agg_df["avg_return_1d"].apply(format_pct),
            "Avg 5d": agg_df["avg_return_5d"].apply(format_pct),
            "Avg 20d": agg_df["avg_return_20d"].apply(format_pct),
            "% Breakout": agg_df["pct_near_breakout"].apply(format_pct),
            "% Breakdown": agg_df["pct_near_breakdown"].apply(format_pct),
            "Avg Vol Ratio": agg_df["avg_vol_ratio"].apply(format_ratio),
            "Avg ApeWisdom Vel": agg_df["avg_apewisdom_velocity"].apply(_fmt_vel),
            "Sector Health": agg_df["sector_health"].apply(health_label),
        }
    )

    sector_event = st.dataframe(
        display_agg,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "Sector": st.column_config.TextColumn(width="medium"),
            "# Tickers": st.column_config.NumberColumn(width="small"),
            "Sector Health": st.column_config.TextColumn(width="small"),
        },
    )

    if sector_event.selection.rows:
        selected_idx = sector_event.selection.rows[0]
        sector_id = agg_df.index[selected_idx]
        st.session_state["preselect_sector"] = sector_id
        st.switch_page("pages/01_All_Tickers.py")
else:
    st.info("No signal data available yet — run the daily refresh job first.")

st.divider()

# ── Per-sector spotlight cards ────────────────────────────────────────────────
signals_df = load_signals_matrix()
universe_data = load_universe_for_ui()
sectors = universe_data["sectors"]

sector_items = list(sectors.values())
for row_start in range(0, len(sector_items), 4):
    cols = st.columns(4)
    for col_idx, sector in enumerate(sector_items[row_start : row_start + 4]):
        with cols[col_idx]:
            sector_card(
                sector_id=sector.id,
                display_name=sector.display_name,
                description=sector.description,
                tickers_in_sector=sector.tickers,
                latest_signals_df=signals_df,
                speculative=sector.speculative,
            )
