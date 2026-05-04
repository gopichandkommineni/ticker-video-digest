"""Ticker Detail page — signals, price chart, and recent news for one ticker."""
import pandas as pd
import streamlit as st

from casino_dashboard.ui.formatting import format_money, format_pct, format_ratio
from casino_dashboard.ui.loaders import (
    load_news_for_ticker,
    load_price_history,
    load_signals_matrix,
    load_universe_for_ui,
)

st.set_page_config(page_title="Ticker Detail — Casino Dashboard", layout="wide")

universe_data = load_universe_for_ui()
sectors = universe_data["sectors"]
ticker_to_sectors = universe_data["ticker_to_sectors"]
all_tickers = sorted(ticker_to_sectors.keys())

# ── Ticker selection ──────────────────────────────────────────────────────────
ticker = st.query_params.get("ticker", None)
if not ticker or ticker not in all_tickers:
    ticker = st.selectbox("Select ticker", options=all_tickers, index=0)

if not ticker:
    st.info("Select a ticker to view details.")
    st.stop()

# ── Company name (best-effort from yfinance) ──────────────────────────────────
@st.cache_data(ttl=86400)
def _company_name(t: str) -> str:
    try:
        import yfinance as yf

        info = yf.Ticker(t).info
        return info.get("longName") or info.get("shortName") or t
    except Exception:
        return t


company_name = _company_name(ticker)
st.title(f"{ticker} — {company_name}")

# ── Sector badges ─────────────────────────────────────────────────────────────
sector_ids = ticker_to_sectors.get(ticker, [])
if sector_ids:
    badges = "  ".join(
        f"**{sectors[s].display_name}**" for s in sector_ids if s in sectors
    )
    st.markdown(badges)

# ── Signal dict for this ticker ───────────────────────────────────────────────
signals_df = load_signals_matrix()
sig: dict = {}
if not signals_df.empty and ticker in signals_df.index:
    sig = {k: v for k, v in signals_df.loc[ticker].items() if pd.notna(v)}

# ── Key metrics row ───────────────────────────────────────────────────────────
price_df = load_price_history(ticker, days=1)
close_raw: float | None = None
if not price_df.empty:
    close_raw = float(price_df["close"].iloc[-1])

return_1d = sig.get("return_1d")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Close",
        format_money(close_raw),
        delta=format_pct(return_1d) if return_1d is not None else None,
    )
with col2:
    st.metric("Vol Ratio 30d", format_ratio(sig.get("vol_ratio_30d")))
with col3:
    st.metric("5d Return", format_pct(sig.get("return_5d")))
with col4:
    st.metric("20d Return", format_pct(sig.get("return_20d")))

# ── Price chart ───────────────────────────────────────────────────────────────
st.subheader("Price History (60 days)")
history_df = load_price_history(ticker, days=60)
if not history_df.empty:
    chart_df = history_df.set_index("date")[["close"]].rename(columns={"close": "Close"})
    st.line_chart(chart_df)
else:
    st.info("No price history available.")

# ── Signals table + News side by side ────────────────────────────────────────
left, right = st.columns(2)

with left:
    st.subheader("All Signals")
    if sig:
        signal_rows = [
            {"Signal": k, "Value": f"{v:.4f}" if isinstance(v, float) else str(v)}
            for k, v in sorted(sig.items())
        ]
        st.dataframe(
            pd.DataFrame(signal_rows), hide_index=True, use_container_width=True
        )
    else:
        st.info("No signals available for this ticker.")

with right:
    st.subheader("Recent News")
    news_items = load_news_for_ticker(ticker, limit=5)
    if news_items:
        for item in news_items:
            title = item.title or "Untitled"
            publisher = item.publisher or "Unknown"
            if not item.title and not item.publisher and not item.link:
                continue
            if item.link:
                st.markdown(f"- **{publisher}** — [{title}]({item.link})")
            else:
                st.markdown(f"- **{publisher}** — {title}")
    else:
        st.info("No recent news available.")
