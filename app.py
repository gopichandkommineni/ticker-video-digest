"""Stock Momentum Dashboard — Sectors Overview (root page)."""
import streamlit as st

st.set_page_config(page_title="Stock Dashboard", layout="wide")

from casino_dashboard.ui.loaders import load_signals_matrix, load_universe_for_ui  # noqa: E402
from casino_dashboard.ui.sector_card import sector_card  # noqa: E402

st.title("Stock Momentum Dashboard")
st.caption(
    "Daily refreshed signals across 8 narrative themes. "
    "Read STRATEGY.md for thesis. Not investment advice."
)

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
