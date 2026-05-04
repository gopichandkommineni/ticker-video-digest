"""Ticker Detail page — signals, price chart, and recent news for one ticker."""
import altair as alt
import pandas as pd
import streamlit as st

from casino_dashboard.ui.external_links import build_external_links
from casino_dashboard.ui.formatting import format_money, format_pct, format_ratio
from casino_dashboard.ui.indicators import compute_bollinger, compute_rsi, compute_sma
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

# ── External research links ───────────────────────────────────────────────────
_link_pills = "  ".join(
    f'<a href="{url}" target="_blank" rel="noopener" '
    f'style="display:inline-block;padding:2px 10px;margin:2px;border-radius:12px;'
    f'border:1px solid #888;font-size:0.8rem;text-decoration:none;color:inherit;">'
    f"{label}</a>"
    for label, url in build_external_links(ticker)
)
st.markdown(_link_pills, unsafe_allow_html=True)

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

# ── Price chart with technical indicators ────────────────────────────────────
st.subheader("Price History (60 days) with Technical Indicators")

history_df = load_price_history(ticker, days=210)  # extra history for 200d MA warmup

if not history_df.empty:
    history_df = history_df.copy()
    history_df["date"] = pd.to_datetime(history_df["date"])
    prices = history_df["close"]

    # Compute indicators
    history_df["sma_20"] = compute_sma(prices, 20)
    history_df["sma_50"] = compute_sma(prices, 50)
    history_df["sma_200"] = compute_sma(prices, 200)
    bb_middle, bb_upper, bb_lower = compute_bollinger(prices, window=20)
    history_df["bb_upper"] = bb_upper
    history_df["bb_lower"] = bb_lower
    history_df["rsi"] = compute_rsi(prices, window=14)

    # Restrict display window to last 60 days
    display_df = history_df.tail(60).reset_index(drop=True)

    has_200d = display_df["sma_200"].notna().any()

    base = alt.Chart(display_df).encode(
        x=alt.X("date:T", axis=alt.Axis(title="Date", format="%b %d"))
    )

    # Bollinger band fill (area between upper and lower)
    bb_area = (
        alt.Chart(display_df)
        .mark_area(opacity=0.15, color="gray")
        .encode(
            x=alt.X("date:T"),
            y=alt.Y("bb_lower:Q", title="Price ($)"),
            y2=alt.Y2("bb_upper:Q"),
        )
        .transform_filter(alt.datum.bb_lower != None)  # noqa: E711
    )

    # Price line
    price_line = base.mark_line(color="#1f77b4", strokeWidth=2).encode(
        y=alt.Y("close:Q", title="Price ($)"),
        tooltip=[
            alt.Tooltip("date:T", title="Date", format="%Y-%m-%d"),
            alt.Tooltip("close:Q", title="Close", format="$.2f"),
            alt.Tooltip("sma_20:Q", title="SMA 20", format="$.2f"),
            alt.Tooltip("sma_50:Q", title="SMA 50", format="$.2f"),
            alt.Tooltip("bb_upper:Q", title="BB Upper", format="$.2f"),
            alt.Tooltip("bb_lower:Q", title="BB Lower", format="$.2f"),
        ],
    )

    sma20_line = base.mark_line(color="#ff7f0e", strokeWidth=1.5, strokeDash=[4, 2]).encode(
        y=alt.Y("sma_20:Q"),
    ).transform_filter(alt.datum.sma_20 != None)  # noqa: E711

    sma50_line = base.mark_line(color="#2ca02c", strokeWidth=1.5, strokeDash=[4, 2]).encode(
        y=alt.Y("sma_50:Q"),
    ).transform_filter(alt.datum.sma_50 != None)  # noqa: E711

    layers = [bb_area, price_line, sma20_line, sma50_line]

    if has_200d:
        sma200_line = (
            base.mark_line(color="#d62728", strokeWidth=1.5, strokeDash=[6, 3])
            .encode(y=alt.Y("sma_200:Q"))
            .transform_filter(alt.datum.sma_200 != None)  # noqa: E711
        )
        layers.append(sma200_line)

    main_chart = (
        alt.layer(*layers)
        .properties(height=400)
        .resolve_scale(y="shared")
    )

    # RSI sub-panel
    rsi_base = alt.Chart(display_df).encode(
        x=alt.X("date:T", axis=alt.Axis(title="", format="%b %d"))
    )

    rsi_line = rsi_base.mark_line(color="#9467bd", strokeWidth=1.5).encode(
        y=alt.Y(
            "rsi:Q",
            scale=alt.Scale(domain=[0, 100]),
            title="RSI (14)",
        ),
        tooltip=[
            alt.Tooltip("date:T", title="Date", format="%Y-%m-%d"),
            alt.Tooltip("rsi:Q", title="RSI 14", format=".1f"),
        ],
    ).transform_filter(alt.datum.rsi != None)  # noqa: E711

    # Reference lines at 30 and 70
    oversold_df = pd.DataFrame({"y": [30]})
    overbought_df = pd.DataFrame({"y": [70]})

    oversold_rule = (
        alt.Chart(oversold_df)
        .mark_rule(color="green", strokeDash=[4, 2], opacity=0.6)
        .encode(y=alt.Y("y:Q", scale=alt.Scale(domain=[0, 100])))
    )
    overbought_rule = (
        alt.Chart(overbought_df)
        .mark_rule(color="red", strokeDash=[4, 2], opacity=0.6)
        .encode(y=alt.Y("y:Q", scale=alt.Scale(domain=[0, 100])))
    )

    rsi_panel = (
        alt.layer(rsi_line, oversold_rule, overbought_rule)
        .properties(height=150)
    )

    full_chart = alt.vconcat(main_chart, rsi_panel).resolve_scale(x="shared")

    st.altair_chart(full_chart, use_container_width=True)

    # Legend
    legend_parts = [
        "**Chart legend:** Blue = Close price",
        "Orange dashed = 20-day SMA",
        "Green dashed = 50-day SMA",
    ]
    if has_200d:
        legend_parts.append("Red dashed = 200-day SMA")
    legend_parts += [
        "Gray fill = Bollinger Bands (20d, ±2σ)",
        "Purple = RSI 14 · Green line = 30 (oversold) · Red line = 70 (overbought)",
    ]
    st.caption("  |  ".join(legend_parts))
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
