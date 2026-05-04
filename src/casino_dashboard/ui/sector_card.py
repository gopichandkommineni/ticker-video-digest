"""Sector card component for the Casino Dashboard overview page."""
import pandas as pd
import streamlit as st

from casino_dashboard.ui.formatting import color_for_return, format_pct


def sector_card(
    sector_id: str,
    display_name: str,
    description: str,
    tickers_in_sector: list[str],
    latest_signals_df: pd.DataFrame,
    speculative: bool,
) -> None:
    """Render a bordered card for one sector with key momentum stats."""
    with st.container(border=True):
        header = f"**{display_name}**"
        if speculative:
            header += " :orange[SPECULATIVE]"
        st.markdown(header)
        st.caption(description)

        avg_5d_return: float | None = None
        pct_near_breakout: float | None = None

        if not latest_signals_df.empty:
            mask = latest_signals_df.index.isin(tickers_in_sector)
            sector_df = latest_signals_df[mask]
            if not sector_df.empty:
                if "return_5d" in sector_df.columns:
                    vals = sector_df["return_5d"].dropna()
                    if not vals.empty:
                        avg_5d_return = float(vals.mean())
                if "near_breakout" in sector_df.columns:
                    vals = sector_df["near_breakout"].dropna()
                    if not vals.empty:
                        pct_near_breakout = float((vals > 0).mean() * 100)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**{len(tickers_in_sector)}** tickers")
            if avg_5d_return is not None:
                color = color_for_return(avg_5d_return)
                st.markdown(f"Avg 5d: :{color}[{format_pct(avg_5d_return)}]")
            else:
                st.markdown("Avg 5d: —")
        with col2:
            if pct_near_breakout is not None:
                st.markdown(f"Near BO: {format_pct(pct_near_breakout)}")
            else:
                st.markdown("Near BO: —")

        if st.button("View →", key=f"sector_card_{sector_id}"):
            st.query_params["sector"] = sector_id
            st.switch_page("pages/01_All_Tickers.py")
