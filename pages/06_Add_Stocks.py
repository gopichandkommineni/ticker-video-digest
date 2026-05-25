"""Add Stocks — add tickers to the dashboard universe."""
import math
import re
import threading
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

from casino_dashboard.data.ticker_validation import validate_ticker
from casino_dashboard.db.repository import (
    add_user_theme,
    add_user_ticker,
    get_user_added_themes,
    get_user_added_tickers,
    remove_user_ticker,
    set_user_ticker_status,
)
from casino_dashboard.db.schema import _DEFAULT_DB_PATH, init_db
from casino_dashboard.jobs.daily_refresh import refresh_single_ticker
from casino_dashboard.ui.loaders import load_universe_for_ui

_DB_PATH = _DEFAULT_DB_PATH

st.set_page_config(page_title="Add Stocks", layout="wide")
st.title("Add Stocks")
st.caption(
    "Add tickers to the dashboard universe. "
    "YAML-defined tickers are curated and cannot be removed here."
)

# Ensure the schema tables exist before any write.
init_db(_DB_PATH)


def _str(val: object, default: str = "—") -> str:
    """Convert a pandas/SQLite cell value to str, treating None/NaN as default."""
    if val is None:
        return default
    if isinstance(val, float) and math.isnan(val):
        return default
    s = str(val).strip()
    return s if s else default


def _slugify(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")


def _spawn_refresh(ticker: str, db_path: Path) -> None:
    """Run refresh_single_ticker in a background daemon thread."""
    def _worker():
        success, error = refresh_single_ticker(ticker, db_path)
        now_iso = datetime.now(tz=timezone.utc).isoformat()
        if success:
            set_user_ticker_status(ticker, "complete", None, now_iso, db_path)
        else:
            set_user_ticker_status(ticker, "failed", error, now_iso, db_path)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()


# ---------------------------------------------------------------------------
# Section A — Add a ticker
# ---------------------------------------------------------------------------

st.subheader("Add a ticker")

# Use plain widgets (not st.form) so the theme selector triggers reruns and
# the "Create new theme" fields appear dynamically without waiting for submit.
universe_data = load_universe_for_ui()
yaml_theme_ids: set[str] = set(universe_data["sectors"].keys())

user_themes_df = get_user_added_themes(_DB_PATH)
user_theme_ids = set(user_themes_df["theme_id"].tolist()) if not user_themes_df.empty else set()
all_theme_ids = sorted(yaml_theme_ids | user_theme_ids)

theme_display: dict[str, str] = {}
for tid in all_theme_ids:
    if tid in universe_data["sectors"]:
        theme_display[tid] = universe_data["sectors"][tid].display_name
    elif not user_themes_df.empty and tid in user_themes_df["theme_id"].values:
        _trow = user_themes_df[user_themes_df["theme_id"] == tid].iloc[0]
        theme_display[tid] = _trow["display_name"]
    else:
        theme_display[tid] = tid

theme_options = all_theme_ids + ["+ Create new theme"]
theme_labels = [theme_display.get(t, t) for t in all_theme_ids] + ["+ Create new theme"]
label_to_id = dict(zip(theme_labels, theme_options))

raw_ticker = st.text_input("Ticker symbol", placeholder="e.g. PLTR", key="add_ticker_input")
selected_label = st.selectbox("Theme", options=theme_labels, key="add_theme_select")
selected_theme_option = label_to_id[selected_label]

new_theme_display_name = ""
new_theme_description = ""
new_theme_speculative = False
if selected_theme_option == "+ Create new theme":
    new_theme_display_name = st.text_input("New theme name (required)", key="new_theme_name")
    new_theme_description = st.text_area("Theme description (required)", key="new_theme_desc")
    new_theme_speculative = st.checkbox("Speculative theme", key="new_theme_spec")

added_by = st.text_input("Added by (optional)", placeholder="your name", key="add_added_by")

submitted = st.button("Add ticker", type="primary")

if submitted:
    ticker = raw_ticker.strip().upper()

    if not ticker:
        st.error("Please enter a ticker symbol.")
        st.stop()

    # Collision check across the full merged universe.
    universe_data = load_universe_for_ui()
    all_universe_tickers = set(universe_data["ticker_to_sectors"].keys())
    if ticker in all_universe_tickers:
        sectors_for_ticker = universe_data["ticker_to_sectors"].get(ticker, [])
        sector_names = [
            universe_data["sectors"][s].display_name
            for s in sectors_for_ticker
            if s in universe_data["sectors"]
        ]
        theme_str = ", ".join(sector_names) if sector_names else "unknown"
        st.error(f"**{ticker}** is already in the universe under: {theme_str}")
        st.stop()

    # Validate ticker via yfinance (one live call, user-triggered).
    with st.spinner(f"Validating {ticker}…"):
        is_valid, company_name, error_msg = validate_ticker(ticker)
    if not is_valid:
        st.error(f"Ticker rejected: {error_msg}")
        st.stop()

    # Handle new theme creation.
    theme_id_to_use = selected_theme_option
    if selected_theme_option == "+ Create new theme":
        if not new_theme_display_name.strip():
            st.error("Please enter a theme name.")
            st.stop()
        if not new_theme_description.strip():
            st.error("Please enter a theme description.")
            st.stop()
        theme_id_to_use = _slugify(new_theme_display_name)
        if not theme_id_to_use:
            st.error("Theme name could not be converted to a valid ID.")
            st.stop()
        # Collision check for theme slug.
        all_known_theme_ids = yaml_theme_ids | user_theme_ids
        if theme_id_to_use in all_known_theme_ids:
            st.error(
                f"Theme slug **{theme_id_to_use}** conflicts with an existing theme. "
                "Choose a different name."
            )
            st.stop()
        try:
            add_user_theme(
                theme_id=theme_id_to_use,
                display_name=new_theme_display_name.strip(),
                description=new_theme_description.strip(),
                speculative=new_theme_speculative,
                created_by=added_by.strip() or None,
                db_path=_DB_PATH,
            )
        except ValueError as exc:
            st.error(str(exc))
            st.stop()

    # Insert the ticker as pending.
    try:
        add_user_ticker(
            ticker=ticker,
            theme_id=theme_id_to_use,
            company_name=company_name,
            added_by=added_by.strip() or None,
            db_path=_DB_PATH,
        )
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    # Kick off background fetch.
    _spawn_refresh(ticker, _DB_PATH)

    # Clear cached universe so other pages see the new ticker immediately.
    load_universe_for_ui.clear()

    # Reset input fields by clearing their session_state keys.
    for _k in ("add_ticker_input", "add_theme_select", "new_theme_name",
                "new_theme_desc", "new_theme_spec", "add_added_by"):
        st.session_state.pop(_k, None)

    st.success(f"Added **{ticker}** ({company_name}) — fetching data now… (status: ⏳ Fetching)")
    st.rerun()


# ---------------------------------------------------------------------------
# Section B — Current user-added universe (with live status polling)
# ---------------------------------------------------------------------------

st.subheader("User-added tickers")


def _render_status(status: str, detail: str | None) -> str:
    if status == "pending":
        return "⏳ Fetching…"
    if status == "complete":
        return "✓ Ready"
    if status == "failed":
        return f"✗ Failed: {detail or 'unknown error'}"
    return status


@st.fragment(run_every=5)
def _status_section() -> None:
    df = get_user_added_tickers(_DB_PATH)

    if df.empty:
        st.info("No user-added tickers yet. Use the form above to add one.")
        return

    has_pending = (df["status"] == "pending").any()
    if has_pending:
        st.caption("Auto-refreshing every 5 s while fetches are in progress…")

    # Build display rows with a Remove button per row.
    # Use st.data_editor is not ideal here since we need per-row buttons.
    # Instead, render a header row followed by one row per ticker.
    universe_data = load_universe_for_ui()
    sectors = universe_data["sectors"]

    header_cols = st.columns([1, 2, 2, 2, 2, 1])
    header_cols[0].markdown("**Ticker**")
    header_cols[1].markdown("**Company**")
    header_cols[2].markdown("**Theme**")
    header_cols[3].markdown("**Status**")
    header_cols[4].markdown("**Added by / at**")
    header_cols[5].markdown("**Action**")

    for _, row in df.iterrows():
        ticker = row["ticker"]
        theme_id = row["theme_id"]
        theme_name = sectors[theme_id].display_name if theme_id in sectors else theme_id
        status_text = _render_status(row["status"], row.get("status_detail"))
        added_info = _str(row.get("added_by")) + "\n" + _str(row.get("added_at"), "")[:10]

        cols = st.columns([1, 2, 2, 2, 2, 1])
        cols[0].write(ticker)
        cols[1].write(_str(row.get("company_name")))
        cols[2].write(theme_name)
        cols[3].write(status_text)
        cols[4].write(added_info)
        if cols[5].button("Remove", key=f"remove_{ticker}"):
            remove_user_ticker(ticker, _DB_PATH)
            load_universe_for_ui.clear()
            st.rerun()


_status_section()


# ---------------------------------------------------------------------------
# Section C — Core universe (read-only, curated)
# ---------------------------------------------------------------------------

with st.expander("Full universe"):
    universe_data = load_universe_for_ui()
    user_df = get_user_added_tickers(_DB_PATH)
    user_complete = (
        set(user_df.loc[user_df["status"] == "complete", "ticker"].tolist())
        if not user_df.empty else set()
    )
    user_pending = (
        set(user_df.loc[user_df["status"] == "pending", "ticker"].tolist())
        if not user_df.empty else set()
    )

    for sector_id, sector in universe_data["sectors"].items():
        parts = []
        for t in sector.tickers:
            if t in user_complete:
                parts.append(f"{t} ✓")
            elif t in user_pending:
                parts.append(f"{t} ⏳")
            else:
                parts.append(t)
        if parts:
            st.markdown(f"**{sector.display_name}**: {', '.join(parts)}")
