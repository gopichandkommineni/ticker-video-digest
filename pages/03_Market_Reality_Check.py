"""Market Reality Check — composite Reality Score, indicators, Claude thesis."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from ticker_digest import config
from ticker_digest.market import compute_reality_score, generate_thesis, get_snapshot
from ticker_digest.models import MarketSnapshot, RealityScore

st.set_page_config(page_title="Market Reality Check — Stock Dashboard", layout="wide")

_BAND_COLORS = {
    "severe_decoupling": "#b71c1c",
    "stretched": "#ef6c00",
    "aligned": "#2e7d32",
    "market_discounting_weakness": "#1565c0",
}

_BAND_LABELS = {
    "severe_decoupling": "Severe decoupling — euphoric",
    "stretched": "Stretched",
    "aligned": "Aligned",
    "market_discounting_weakness": "Market discounting weakness",
}


def _render_score_card(score: RealityScore) -> None:
    color = _BAND_COLORS.get(score.band, "#424242")
    label = _BAND_LABELS.get(score.band, score.band)
    st.markdown(
        f"""
        <div style="padding:18px;border-radius:8px;background:{color};color:white;">
            <div style="font-size:14px;opacity:0.85;">REALITY SCORE</div>
            <div style="font-size:48px;font-weight:600;line-height:1.1;">{score.score:+.2f}</div>
            <div style="font-size:18px;margin-top:4px;">{label}</div>
            <div style="font-size:13px;opacity:0.85;margin-top:8px;">
                market z: {score.market_z if score.market_z is not None else 'n/a'}
                &nbsp;·&nbsp;
                economy z: {score.economy_z if score.economy_z is not None else 'n/a'}
                &nbsp;·&nbsp;
                {len(score.used_indicators)} of {len(score.used_indicators) + len(score.skipped_indicators)} indicators used
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_contributions(score: RealityScore) -> None:
    if not score.contributions:
        st.info("No contributing indicators.")
        return
    df = (
        pd.DataFrame(
            [{"indicator": k, "signed_z": v} for k, v in score.contributions.items()]
        )
        .sort_values("signed_z", key=lambda s: s.abs(), ascending=False)
        .set_index("indicator")
    )
    st.bar_chart(df, horizontal=True, height=320)


def _render_indicator_table(snapshot: MarketSnapshot, bucket: str, title: str) -> None:
    st.subheader(title)
    rows = []
    for sid, ind in snapshot.indicators.items():
        if ind.bucket != bucket:
            continue
        rows.append(
            {
                "id": sid,
                "name": ind.name,
                "value": ind.value,
                "z": ind.z_score,
                "as_of": ind.as_of.date().isoformat() if ind.as_of else None,
                "status": "ok" if ind.error is None else ind.error,
            }
        )
    if not rows:
        st.write("_no data_")
        return
    df = pd.DataFrame(rows).set_index("id")
    st.dataframe(df, width="stretch")

    for sid, ind in snapshot.indicators.items():
        if ind.bucket != bucket or not ind.history:
            continue
        with st.expander(f"{sid} — {ind.name}"):
            spark = pd.Series(ind.history)
            spark.index = pd.DatetimeIndex(spark.index)
            st.line_chart(spark, height=140)


st.title("Broader Market Reality Check")
st.write(
    "Composite of US market & real-economy indicators. Positive scores = "
    "market priced richer than the real economy supports; negative scores = "
    "market discounting weakness."
)

if not config.FRED_API_KEY:
    st.warning(
        "FRED_API_KEY not configured — economy bucket will be sparse. "
        "Get a free key at https://fred.stlouisfed.org/docs/api/api_key.html "
        "and set it in your environment or .env file."
    )

refresh = st.button("Force refresh (bypass cache)")
with st.spinner("Loading indicators…"):
    snapshot = get_snapshot(force=refresh)
    score = compute_reality_score(snapshot)

top = st.columns([2, 3])
with top[0]:
    _render_score_card(score)
    vix = snapshot.indicators.get("VIX")
    if vix and vix.value is not None:
        st.metric("VIX (context)", f"{vix.value:.2f}", help="Excluded from the composite.")
with top[1]:
    st.subheader("Thesis")
    if st.button("Generate / refresh thesis"):
        with st.spinner("Asking Claude…"):
            try:
                thesis = generate_thesis(snapshot, score, use_cache=not refresh)
                st.session_state["market_thesis"] = thesis.model_dump()
            except Exception as exc:  # noqa: BLE001
                st.error(f"Thesis generation failed: {exc}")
    thesis_data = st.session_state.get("market_thesis")
    if thesis_data:
        st.markdown(f"**Regime:** `{thesis_data['regime']}`")
        st.write(thesis_data["narrative"])
        cols = st.columns(2)
        with cols[0]:
            st.markdown("**Bull case**")
            for b in thesis_data["bull_case"]:
                st.markdown(f"- {b}")
        with cols[1]:
            st.markdown("**Bear case**")
            for b in thesis_data["bear_case"]:
                st.markdown(f"- {b}")
        st.markdown("**Watch items**")
        for w in thesis_data["key_watch_items"]:
            st.markdown(f"- {w}")
    else:
        st.caption("Click *Generate / refresh thesis* to call Claude on the current snapshot.")

st.subheader("Per-indicator contributions to score")
_render_contributions(score)

cols = st.columns(2)
with cols[0]:
    _render_indicator_table(snapshot, "market", "Market & sentiment indicators")
with cols[1]:
    _render_indicator_table(snapshot, "economy", "Real-economy indicators")

st.caption(
    "Not investment advice. Aggregated from FRED, Yahoo Finance, and Claude-generated synthesis."
)
