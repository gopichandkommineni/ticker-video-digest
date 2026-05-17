"""Congress trades page — skeleton render (PR 1 of 2).

Displays two raw data tables: committee view and star-trader view.
Heatmap and styling polish are in the follow-up PR.
"""
import streamlit as st

from casino_dashboard.ui.loaders import (
    get_last_congress_refresh_timestamp,
    load_committee_trades_table,
    load_star_trader_trades_table,
)

st.set_page_config(page_title="Congress Trades", layout="wide")

st.title("Congress trades")
st.caption(
    "Disclosures filed under the STOCK Act. 45-day max lag from "
    "trade to disclosure. Amounts are reported in ranges; "
    "midpoints shown. Not investment advice."
)

# Section 1: Committee view
st.subheader("Committee chairs and ranking members")
st.caption(
    "Members who chair or rank on committees with insider access "
    "to defense, financial, energy, intelligence, foreign affairs, "
    "or science/tech policy. Trades from the last 90 days."
)
committee_df = load_committee_trades_table()
if committee_df.empty:
    st.info(
        "No committee trade data yet. Run the daily refresh job to populate "
        "congress_members and congress_trades tables."
    )
else:
    st.dataframe(committee_df, use_container_width=True)

# Section 2: Star-trader view
st.subheader("Star traders")
st.caption(
    "Hand-curated list of congressional traders with public "
    "outperformance track records. See config/star_traders.yaml."
)
star_df = load_star_trader_trades_table()
if star_df.empty:
    st.info(
        "No star-trader data yet. Run the daily refresh job to populate "
        "congress_trades, or check that FMP_API_KEY is set."
    )
else:
    st.dataframe(star_df, use_container_width=True)

# Section 3: Last refresh
st.caption(f"Last refresh: {get_last_congress_refresh_timestamp()}")
