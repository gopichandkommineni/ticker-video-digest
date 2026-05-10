"""All Tickers page — filterable, sortable table of every ticker in the universe."""
import pandas as pd
import streamlit as st

from casino_dashboard.db.repository import save_user_annotations
from casino_dashboard.ui.formatting import (
    format_mention_velocity,
    format_money,
    format_ratio,
    format_rsi,
)
from casino_dashboard.ui.loaders import (
    load_latest_prices,
    load_latest_social_mentions,
    load_manual_notes_all,
    load_signals_matrix,
    load_universe_for_ui,
    resolve_sector_default,
)

st.set_page_config(page_title="All Tickers — Stock Dashboard", layout="wide")
st.title("All Tickers")

signals_df = load_signals_matrix()
prices_df = load_latest_prices()
social_df = load_latest_social_mentions()
universe_data = load_universe_for_ui()
sectors = universe_data["sectors"]
ticker_to_sectors = universe_data["ticker_to_sectors"]
notes_df = load_manual_notes_all()

all_sector_ids = list(sectors.keys())
default_sectors = resolve_sector_default(st.session_state, st.query_params, all_sector_ids)

# ── Filters ──────────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

with col1:
    selected_sectors = st.multiselect(
        "Sector",
        options=all_sector_ids,
        default=default_sectors,
        format_func=lambda s: sectors[s].display_name,
    )

with col2:
    near_breakout_only = st.checkbox("Near breakout only")

with col3:
    near_breakdown_only = st.checkbox("Near breakdown only")

with col4:
    speculative_only = st.checkbox("Speculative sectors only")

# ── Build rows ────────────────────────────────────────────────────────────────
candidate_tickers = [
    ticker
    for ticker, sector_list in ticker_to_sectors.items()
    if any(s in selected_sectors for s in sector_list)
]

if speculative_only:
    candidate_tickers = [
        t
        for t in candidate_tickers
        if any(
            sectors[s].speculative
            for s in ticker_to_sectors.get(t, [])
            if s in sectors
        )
    ]

rows = []
for ticker in candidate_tickers:
    sector_names = [
        sectors[s].display_name
        for s in ticker_to_sectors.get(ticker, [])
        if s in sectors
    ]

    sig: dict = {}
    if not signals_df.empty and ticker in signals_df.index:
        sig = {k: v for k, v in signals_df.loc[ticker].items() if pd.notna(v)}

    close: float | None = None
    if not prices_df.empty and ticker in prices_df.index:
        close = float(prices_df.loc[ticker, "close"])

    near_bo = float(sig.get("near_breakout", 0) or 0)
    near_bd = float(sig.get("near_breakdown", 0) or 0)
    flags = " ".join(
        (["BREAKOUT"] if near_bo else []) + (["BREAKDOWN"] if near_bd else [])
    )

    mention_velocity: float | None = sig.get("apewisdom_velocity_24h")

    if not notes_df.empty and ticker in notes_df.index:
        note_row = notes_df.loc[ticker]
        user_notes = str(note_row.get("notes") or "")
        user_tags = str(note_row.get("tags") or "")
    else:
        user_notes = ""
        user_tags = ""

    rows.append(
        {
            "_ticker": ticker,
            "Ticker": f"/Ticker_Detail?ticker={ticker}",
            "Sectors": ", ".join(sector_names),
            "_close_raw": close,
            "_vol_ratio_raw": sig.get("vol_ratio_30d"),
            "_mention_velocity_raw": mention_velocity,
            "_vol_rsi_raw": sig.get("vol_rsi_14"),
            "_near_breakout": near_bo,
            "_near_breakdown": near_bd,
            "Flags": flags,
            "Notes": user_notes,
            "Tags": user_tags,
        }
    )

df = pd.DataFrame(rows) if rows else pd.DataFrame()

# ── Apply flag filters ────────────────────────────────────────────────────────
if not df.empty and near_breakout_only:
    df = df[df["_near_breakout"] > 0]

if not df.empty and near_breakdown_only:
    df = df[df["_near_breakdown"] > 0]

# ── Sort by vol ratio descending ──────────────────────────────────────────────
if not df.empty:
    df = df.sort_values("_vol_ratio_raw", ascending=False, na_position="last")

# ── Build display DataFrame ───────────────────────────────────────────────────
if df.empty:
    st.info("No tickers match the selected filters.")
    st.stop()

display_df = pd.DataFrame(
    {
        "Ticker": df["Ticker"],
        "Sectors": df["Sectors"],
        "Close": df["_close_raw"].apply(format_money),
        "Vol Ratio": df["_vol_ratio_raw"].apply(format_ratio),
        "Mention Vel": df["_mention_velocity_raw"].apply(format_mention_velocity),
        "Vol RSI": df["_vol_rsi_raw"].apply(format_rsi),
        "Notes": df["Notes"],
        "Tags": df["Tags"],
        "Flags": df["Flags"],
    }
)
display_df.index = df["_ticker"].values

edited_df = st.data_editor(
    display_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Ticker": st.column_config.LinkColumn(
            "Ticker",
            display_text=r"ticker=([A-Za-z]+)",
        ),
        "Notes": st.column_config.TextColumn("Notes", help="Your private notes for this ticker"),
        "Tags": st.column_config.TextColumn("Tags", help="Comma-separated tags, e.g. watchlist, earnings"),
    },
    disabled=["Ticker", "Sectors", "Close", "Vol Ratio", "Mention Vel", "Vol RSI", "Flags"],
    key="tickers_editor",
)

# ── Persist edits ─────────────────────────────────────────────────────────────
changed: list[tuple[str, str, str]] = []
for ticker in display_df.index:
    if ticker not in edited_df.index:
        continue
    orig_notes = display_df.loc[ticker, "Notes"]
    orig_tags = display_df.loc[ticker, "Tags"]
    new_notes = edited_df.loc[ticker, "Notes"]
    new_tags = edited_df.loc[ticker, "Tags"]
    if new_notes != orig_notes or new_tags != orig_tags:
        changed.append((ticker, new_notes, new_tags))

if changed:
    for ticker, notes, tags in changed:
        save_user_annotations(ticker, notes or None, tags or None)
    load_manual_notes_all.clear()
    st.rerun()

st.caption("Mention Vel: ApeWisdom 24h velocity (today ÷ yesterday). 🟢 >2x · 🟡 >1.5x · gray = normal · — = no data yet")
st.caption("Vol RSI: 14-period RSI applied to the volume series. >70 = high volume momentum · <30 = low volume momentum.")
