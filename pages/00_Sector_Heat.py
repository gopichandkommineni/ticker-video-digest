"""Sector Heat — ranking dashboard (spec §4).

New homepage (pages/00_Sector_Heat.py — sorts first in Streamlit sidebar).
Shows 8 thesis sectors across three dimensions: Capital Flows, Hype, Growth.
Click into a sector to see constituent breakdown.
"""
import streamlit as st

from casino_dashboard.db.schema import _DEFAULT_DB_PATH
from casino_dashboard.ui.components.sector_heat_table import (
    render_constituent_table,
    render_sector_heat_table,
)
from casino_dashboard.ui.loaders import (
    load_recent_deals,
    load_sector_constituents_ranking,
    load_sector_heat,
    load_universe_for_ui,
)

st.set_page_config(
    page_title="Sector Heat | Casino Dashboard",
    page_icon="🎰",
    layout="wide",
)

DB = str(_DEFAULT_DB_PATH)

st.title("Sector Heat")
st.caption(
    "Three-dimension sector ranking: Capital Flows · Hype · Growth. "
    "Color coded per column by tercile — green = top third, red = bottom third. "
    "All three dimensions shown independently; no composite score."
)

heat_df = load_sector_heat(DB)
universe_data = load_universe_for_ui()

# ── Main ranking table ──────────────────────────────────────────────────────

selected_sector = render_sector_heat_table(heat_df, universe_data)

# ── In-sector drill-down ────────────────────────────────────────────────────

if selected_sector:
    sectors = universe_data.get("sectors", {})
    sector_obj = sectors.get(selected_sector)
    display_name = sector_obj.display_name if sector_obj else selected_sector

    constituents_df = load_sector_constituents_ranking(selected_sector, DB)
    render_constituent_table(constituents_df, display_name)

    # Recent deals for this sector
    deals_df = load_recent_deals(selected_sector, days=30, db_path=DB)
    if not deals_df.empty:
        with st.expander(f"Recent deals — {display_name} (last 30 days)", expanded=False):
            for _, deal in deals_df.iterrows():
                amount_str = ""
                if deal.get("amount_usd") is not None:
                    try:
                        amt = float(deal["amount_usd"])
                        if amt >= 1_000_000_000:
                            amount_str = f" · **${amt/1e9:.1f}B**"
                        elif amt >= 1_000_000:
                            amount_str = f" · **${amt/1e6:.0f}M**"
                    except (TypeError, ValueError):
                        pass
                deal_type = deal.get("deal_type") or "deal"
                ticker = deal.get("primary_ticker") or ""
                ticker_str = f" `{ticker}`" if ticker else ""
                st.markdown(
                    f"**{deal['date']}**{ticker_str} — {deal['summary']}{amount_str}  "
                    f"<small style='color:#6b7280'>_{deal_type}_</small>",
                    unsafe_allow_html=True,
                )

st.divider()
st.caption(
    "Data refreshed daily at 13:00 UTC via GitHub Actions. "
    "Capital Flows = ETF net flow (calculated from AUM change) + manual deal log. "
    "Photonics shows n/a for ETF flow — no clean ETF fit exists. "
    "Deal log staleness: ⚠️ >14 days, 🔴 >30 days."
)
