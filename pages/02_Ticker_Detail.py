"""Ticker Detail page — per-spec v1.0 tile-based layout."""
import math
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

from casino_dashboard.data.manual_notes_loader import load_manual_notes_from_yaml
from casino_dashboard.ui.components.colors import (
    color_for_analyst_upside,
    color_for_earnings_days,
    color_for_profit_margin,
    color_for_returns,
    color_for_revenue_growth,
    color_for_rsi,
    color_for_setup,
    color_for_short_pct,
    color_for_volume_ratio,
    color_to_hex,
)
from casino_dashboard.ui.components.tile import (
    render_empty_tile,
    render_note_tile,
    render_range_tile,
    render_returns_tile,
    render_tile,
)
from casino_dashboard.ui.external_links import build_external_links
from casino_dashboard.ui.formatters import format_currency, format_market_cap, format_pct
from casino_dashboard.ui.loaders import (
    load_manual_notes_all,
    load_recent_news_all_dates,
    load_signals_for_detail,
    load_latest_snapshot_for_ticker,
    load_ticker_metadata_all,
    load_universe_for_ui,
)

st.set_page_config(page_title="Ticker Detail — Casino Dashboard", layout="wide")

# ── Universe & ticker resolution ─────────────────────────────────────────────
universe_data = load_universe_for_ui()
sectors = universe_data["sectors"]
ticker_to_sectors = universe_data["ticker_to_sectors"]
all_tickers = sorted(ticker_to_sectors.keys())

ticker = st.query_params.get("ticker", None)

if ticker and ticker not in all_tickers:
    st.error(f"Ticker **{ticker}** is not in the universe. [← Back to All Tickers](./01_All_Tickers)")
    st.stop()

if not ticker:
    ticker = st.selectbox("Select ticker", options=all_tickers, index=0)

if not ticker:
    st.info("Select a ticker to view details.")
    st.stop()

# ── Data loading ──────────────────────────────────────────────────────────────

signals_df = load_signals_for_detail()
sig: dict = {}
if not signals_df.empty and ticker in signals_df.index:
    sig = {k: v for k, v in signals_df.loc[ticker].items() if pd.notna(v)}

snap = load_latest_snapshot_for_ticker(ticker)
close_price: float | None = snap["close"] if snap else None
today_volume: int | None = snap["volume"] if snap else None
avg_volume_30d: float | None = snap["avg_volume_30d"] if snap else None
snap_date: date | None = snap["date"] if snap else None

metadata_df = load_ticker_metadata_all()
meta: dict = {}
if not metadata_df.empty and ticker in metadata_df.index:
    row = metadata_df.loc[ticker]
    meta = {
        k: (None if isinstance(v, float) and math.isnan(v) else v)
        for k, v in row.items()
    }

notes_df = load_manual_notes_all()
catalyst: str | None = None
red_flag: str | None = None


def _coerce_note(val: object) -> str | None:
    """Coerce pandas NaN / empty-string / literal 'nan' → None at read time."""
    if val is None:
        return None
    if isinstance(val, float) and val != val:  # NaN
        return None
    s = str(val).strip()
    return None if s.lower() in ("", "nan", "none") else s


if not notes_df.empty and ticker in notes_df.index:
    _n = notes_df.loc[ticker]
    catalyst = _coerce_note(_n.get("catalyst"))
    red_flag = _coerce_note(_n.get("red_flag"))
else:
    # Fallback: YAML (for local dev / first-run before daily_refresh writes to DB)
    try:
        _yaml_notes = load_manual_notes_from_yaml()
        _ticker_notes = _yaml_notes.get(ticker, {})
        catalyst = _ticker_notes.get("catalyst")
        red_flag = _ticker_notes.get("red_flag")
    except Exception:
        pass

news_items = load_recent_news_all_dates(ticker, limit=5)
sector_ids = ticker_to_sectors.get(ticker, [])

# Company name (cached one day since it rarely changes)
@st.cache_data(ttl=86400)
def _company_name(t: str) -> str:
    try:
        import yfinance as yf
        info = yf.Ticker(t).info
        return info.get("longName") or info.get("shortName") or t
    except Exception:
        return t


company_name = _company_name(ticker)

# ── HEADER ────────────────────────────────────────────────────────────────────

st.markdown(
    f"<h1 style='margin-bottom:2px;font-size:2rem;'>{ticker}"
    f"<span style='font-size:1.1rem;font-weight:400;color:#6b7280;margin-left:10px;'>"
    f"{company_name}</span></h1>",
    unsafe_allow_html=True,
)

# Row: sector pills + price + 1d change
h_left, h_right = st.columns([3, 2])

with h_left:
    if sector_ids:
        pills_html = " ".join(
            f'<span style="display:inline-block;padding:2px 10px;margin:2px 4px 2px 0;'
            f'border-radius:12px;background:#f3f4f6;border:1px solid #d1d5db;'
            f'font-size:0.78rem;color:#374151;font-weight:500;">'
            f"{sectors[s].display_name}</span>"
            for s in sector_ids
            if s in sectors
        )
        st.markdown(pills_html, unsafe_allow_html=True)

with h_right:
    return_1d = sig.get("return_1d")
    if close_price is not None:
        change_color = color_to_hex(color_for_returns(return_1d))
        arrow = "↑" if (return_1d or 0) >= 0 else "↓"
        change_badge = ""
        if return_1d is not None:
            change_pct = f"{return_1d:+.1%}"
            change_badge = (
                f'<span style="background:{change_color}22;color:{change_color};'
                f'padding:2px 10px;border-radius:6px;font-size:1rem;font-weight:600;'
                f'margin-left:10px;">{arrow} {change_pct}</span>'
            )
        st.markdown(
            f'<div style="text-align:right;">'
            f'<span style="font-size:1.6rem;font-weight:700;color:var(--text-color);">'
            f"{format_currency(close_price)}</span>"
            f"{change_badge}</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="text-align:right;font-size:1.6rem;font-weight:700;color:#9ca3af;">—</div>',
            unsafe_allow_html=True,
        )

# External linkout pills
_links_html = " ".join(
    f'<a href="{url}" target="_blank" rel="noopener" '
    f'style="display:inline-block;padding:2px 10px;margin:2px 4px 2px 0;'
    f'border-radius:12px;border:1px solid #9ca3af;font-size:0.78rem;'
    f'text-decoration:none;color:#374151;">{label}</a>'
    for label, url in build_external_links(ticker)
)
st.markdown(_links_html, unsafe_allow_html=True)
st.markdown("---")

# ── FUNDAMENTALS STRIP ────────────────────────────────────────────────────────

market_cap = meta.get("market_cap")
revenue_ttm = meta.get("revenue_ttm")
revenue_growth = meta.get("revenue_growth_yoy")
profit_margin = meta.get("profit_margin")
beta = meta.get("beta")

rev_growth_color = color_to_hex(color_for_revenue_growth(revenue_growth))
margin_color = color_to_hex(color_for_profit_margin(profit_margin))

fund_label_css = (
    "font-size:0.68rem;text-transform:uppercase;letter-spacing:0.07em;"
    "color:#9ca3af;font-weight:600;margin-bottom:4px;"
)
fund_value_css = "font-size:1.05rem;font-weight:700;color:{color};"

fund_cells = [
    ("Market Cap", format_market_cap(market_cap), "var(--text-color)"),
    ("Revenue TTM", format_market_cap(revenue_ttm), "var(--text-color)"),
    ("Revenue YoY %", format_pct(revenue_growth), rev_growth_color),
    ("Profit Margin", format_pct(profit_margin), margin_color),
    ("Beta", f"{beta:.2f}" if beta is not None else "—", "var(--text-color)"),
]

fund_cols = st.columns(5)
for col, (label, value, vcolor) in zip(fund_cols, fund_cells):
    with col:
        st.markdown(
            f'<div style="background:var(--secondary-background-color);'
            f'border:1px solid rgba(128,128,128,0.2);'
            f'padding:10px 14px;border-radius:6px;">'
            f'<div style="{fund_label_css}">{label}</div>'
            f'<div style="{fund_value_css.format(color=vcolor)}">{value}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )

st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

# ── TIER 1 TILES (3 columns) ──────────────────────────────────────────────────

t1_c1, t1_c2, t1_c3 = st.columns(3)

with t1_c1:
    near_breakout = sig.get("near_breakout")
    near_breakdown = sig.get("near_breakdown")
    setup_color = color_for_setup(near_breakout, near_breakdown)
    if near_breakout:
        setup_label = "BREAKOUT"
    elif near_breakdown:
        setup_label = "BREAKDOWN"
    else:
        setup_label = "NEUTRAL"

    dist_high = sig.get("dist_from_30d_high_pct")
    if dist_high is not None:
        setup_subline = f"{dist_high:+.1%} from 30d high"
    else:
        setup_subline = None

    render_tile(
        "Setup",
        setup_label,
        subline=setup_subline,
        color=setup_color,
        tier=1,
    )

with t1_c2:
    next_earnings_date = meta.get("next_earnings_date")
    next_earnings_time = meta.get("next_earnings_time")
    last_earnings_date = meta.get("last_earnings_date")

    # Parse date strings if needed
    def _parse_date(d: object) -> date | None:
        if d is None:
            return None
        if isinstance(d, date):
            return d
        try:
            return date.fromisoformat(str(d))
        except (ValueError, TypeError):
            return None

    ned = _parse_date(next_earnings_date)
    led = _parse_date(last_earnings_date)
    today = date.today()

    if ned is not None:
        days_until = (ned - today).days
        earn_color = color_for_earnings_days(days_until)
        earn_primary = f"{days_until} day{'s' if days_until != 1 else ''}"
        time_label = (next_earnings_time or "").upper() if next_earnings_time else ""
        subline1 = ned.strftime("%b %-d, %Y")
        if time_label:
            subline1 += f" · {time_label}"
        subline2 = f"{(today - led).days} days since last" if led else None
        sublines_combined = subline1
        if subline2:
            sublines_combined += f"<br>{subline2}"
        render_tile(
            "Earnings",
            earn_primary,
            subline=sublines_combined,
            color=earn_color,
            tier=1,
        )
    else:
        render_tile("Earnings", "TBD", subline="No earnings date available", tier=1)

with t1_c3:
    render_note_tile(
        "Catalyst",
        catalyst,
        placeholder="+ Add catalyst",
        tier=1,
    )

# ── TIER 2 TILES (5 columns) ──────────────────────────────────────────────────

t2_c1, t2_c2, t2_c3, t2_c4, t2_c5 = st.columns(5)

with t2_c1:
    render_returns_tile(
        return_1d=sig.get("return_1d"),
        return_5d=sig.get("return_5d"),
        return_1m=sig.get("return_1m"),
        return_ytd=sig.get("return_ytd"),
        return_1y=sig.get("return_1y"),
    )

with t2_c2:
    render_range_tile(
        current=close_price,
        high_52w=meta.get("fifty_two_week_high"),
        low_52w=meta.get("fifty_two_week_low"),
    )

with t2_c3:
    mentions_today = sig.get("apewisdom_mentions_today")
    velocity_24h = sig.get("apewisdom_velocity_24h")

    if mentions_today is not None:
        mentions_int = int(mentions_today)
        if velocity_24h is not None:
            vel_color = color_to_hex("green") if velocity_24h >= 2.0 else "inherit"
            vel_str = f'<span style="color:{vel_color};font-weight:600;">{velocity_24h:.1f}x</span> 24h velocity'
        else:
            vel_str = None
        render_tile(
            "Social Attention",
            str(mentions_int),
            subline=vel_str,
            tier=2,
        )
    else:
        render_empty_tile("Social Attention", "Not tracked")

with t2_c4:
    vol_ratio = sig.get("vol_ratio_30d")
    vol_color = color_for_volume_ratio(vol_ratio)
    vol_primary = f"{vol_ratio:.2f}x" if vol_ratio is not None else "—"

    if today_volume is not None and avg_volume_30d is not None and avg_volume_30d > 0:
        vol_subline = (
            f"Today: {today_volume / 1_000_000:.1f}M / "
            f"30d avg: {avg_volume_30d / 1_000_000:.1f}M"
        )
    else:
        vol_subline = None

    render_tile("Volume", vol_primary, subline=vol_subline, color=vol_color, tier=2)

with t2_c5:
    short_pct = meta.get("short_pct_of_float")
    short_ratio = meta.get("short_ratio_days")
    short_color = color_for_short_pct(short_pct)

    if short_pct is not None:
        short_primary = f"{short_pct * 100:.1f}%"
        short_subline = (
            f"{short_ratio:.2f} days to cover" if short_ratio is not None else None
        )
        render_tile(
            "Short Interest",
            short_primary,
            subline=short_subline,
            color=short_color,
            tier=2,
        )
    else:
        render_empty_tile("Short Interest")

# ── TIER 3 TILES (4 columns) ──────────────────────────────────────────────────

t3_c1, t3_c2, t3_c3, t3_c4 = st.columns(4)

with t3_c1:
    rsi_val = sig.get("rsi_14")
    if rsi_val is not None:
        rsi_int = int(round(rsi_val))
        if rsi_val > 70:
            rsi_label = "Overbought"
        elif rsi_val >= 60:
            rsi_label = "Approaching overbought"
        elif rsi_val < 30:
            rsi_label = "Oversold"
        else:
            rsi_label = "Neutral"
        render_tile("RSI (14)", str(rsi_int), subline=rsi_label, color=color_for_rsi(rsi_val), tier=3)
    else:
        render_empty_tile("RSI (14)")

with t3_c2:
    target = meta.get("analyst_target_mean")
    if target is not None and close_price is not None and close_price > 0:
        upside = (target - close_price) / close_price
        upside_color = color_for_analyst_upside(upside)
        upside_hex = color_to_hex(upside_color)
        upside_str = f"{upside:+.1%} upside" if upside >= 0 else f"{upside:.1%} from current"
        upside_subline = (
            f'<span style="color:{upside_hex};font-weight:600;">{upside_str}</span>'
        )
        render_tile("Analyst Target", format_currency(target), subline=upside_subline, tier=3)
    elif target is not None:
        render_tile("Analyst Target", format_currency(target), tier=3)
    else:
        render_empty_tile("Analyst Target")

with t3_c3:
    insiders = meta.get("held_pct_insiders")
    institutions = meta.get("held_pct_institutions")
    if insiders is not None or institutions is not None:
        ins_str = f"Insiders: {insiders * 100:.2f}%" if insiders is not None else "Insiders: —"
        inst_str = f"Institutions: {institutions * 100:.2f}%" if institutions is not None else "Institutions: —"
        ownership_subline = f"{ins_str}<br>{inst_str}"
        render_tile("Ownership", ins_str, subline=inst_str, tier=3)
    else:
        render_empty_tile("Ownership")

with t3_c4:
    render_note_tile(
        "Red Flag",
        red_flag,
        placeholder="+ Add concern",
        tier=3,
    )

# ── RECENT NEWS ───────────────────────────────────────────────────────────────

st.markdown("#### Recent News")

if news_items:
    for item in news_items:
        title = item.title or "Untitled"
        publisher = item.publisher or ""
        if item.link:
            st.markdown(
                f'- **{publisher}** — [{title}]({item.link})',
            )
        else:
            st.markdown(f"- **{publisher}** — {title}")
else:
    st.caption("No recent news available.")

# ── FOOTER ────────────────────────────────────────────────────────────────────

st.markdown("---")
refresh_ts = (
    snap_date.strftime("Last refresh: %Y-%m-%d")
    if snap_date
    else "Last refresh: unknown"
)
st.caption(
    f"{refresh_ts} UTC  ·  "
    "Not investment advice. Aggregated commentary from public sources. "
    "Read STRATEGY.md for thesis."
)
