"""Subreddits — decide which subreddits the Reddit scraper reads for each stock."""
import pandas as pd
import streamlit as st

from core.social_media.reddit.resolver import (
    add_subreddit,
    add_subreddit_auto,
    load_entries,
    remove_entry,
    resolve_company,
    save_resolved,
)
from core.social_media.reddit.subreddit_catalog import UniverseEntry
from casino_dashboard.jobs.subreddit_catalog_run import load_company_names
from casino_dashboard.ui.loaders import load_universe_for_ui

_AUTO = "Work it out (general list if no match)"
_GENERAL = "General list (not one stock)"

st.set_page_config(page_title="Subreddits", layout="wide")
st.title("Subreddits")
st.caption(
    "Which Reddit communities are read for each stock. Find them from a company "
    "name, or add one you already know. Everything is saved to "
    "`config/ticker_subreddits.yaml` — commit that file to keep your changes "
    "(edits made on the hosted dashboard are lost when it redeploys)."
)

universe_tickers = sorted(load_universe_for_ui()["ticker_to_sectors"].keys())

left, right = st.columns(2, gap="large")

# ---------------------------------------------------------------------------
# Input 1 — company name → resolve
# ---------------------------------------------------------------------------

with left:
    st.subheader("Find by company name")
    st.caption(
        "Searches the Reddit archive for communities about the company and "
        "shows the evidence. Nothing is saved until you choose."
    )
    with st.form("resolve_form"):
        query = st.text_input("Company name or ticker", placeholder="e.g. Rocket Lab or RKLB")
        ticker_override = st.text_input(
            "Ticker (optional)",
            placeholder="only if it can't be worked out from the name",
        )
        search = st.form_submit_button("Search", type="primary")

    if search:
        if not query.strip():
            st.error("Enter a company name or ticker.")
        else:
            with st.spinner(f"Searching Reddit for {query.strip()}… (up to a minute)"):
                try:
                    st.session_state["resolve_result"] = resolve_company(
                        query, universe=set(universe_tickers),
                        ticker=ticker_override or None,
                    )
                    st.session_state["resolve_ticker"] = ticker_override.strip().upper()
                except Exception as exc:  # network / archive failure
                    st.session_state.pop("resolve_result", None)
                    st.error(f"Search failed: {exc}")

    result = st.session_state.get("resolve_result")
    if result is not None:
        who = f"**{result.query}**"
        if result.ticker:
            who += f" → **{result.ticker}**"
        if result.company_name:
            who += f" ({result.company_name})"
        st.markdown(who)
        if not result.archive_ok:
            st.warning("The archive didn't answer every search — the list may be incomplete.")
        if result.flag:
            st.info(result.flag)

        if result.candidates:
            rows = []
            for cand in result.candidates:
                m = cand.metrics
                rows.append({
                    "Save": cand.selected,
                    "Subreddit": m.name,
                    "Members": m.subscribers,
                    "Posts / 7d": m.posts_7d if m.measured else None,
                    "Commenters / 7d": m.unique_commenters if m.measured else None,
                    "Verdict": ("✅ " if cand.selected else "✖ ") + ", ".join(cand.reasons),
                })
            edited = st.data_editor(
                pd.DataFrame(rows),
                hide_index=True,
                width="stretch",
                disabled=["Subreddit", "Members", "Posts / 7d", "Commenters / 7d", "Verdict"],
                column_config={
                    "Save": st.column_config.CheckboxColumn(help="Tick the ones to save"),
                    "Members": st.column_config.NumberColumn(format="%d"),
                },
                key="resolve_editor",
            )
            save_under = result.ticker or st.session_state.get("resolve_ticker") or ""
            if not save_under:
                save_under = st.text_input(
                    "Save under ticker", placeholder="couldn't work one out — enter it",
                    key="resolve_save_ticker",
                ).strip().upper()
            if st.button("Save ticked subreddits", disabled=not save_under):
                picked = edited.loc[edited["Save"], "Subreddit"].tolist()
                if not picked:
                    st.warning("Nothing ticked.")
                else:
                    try:
                        saved = save_resolved(result, picked, ticker=save_under)
                    except ValueError as exc:
                        st.error(str(exc))
                    else:
                        if saved:
                            st.success(f"Saved under {save_under}: "
                                       + ", ".join(f"r/{e.name}" for e in saved))
                        else:
                            st.info(f"Already saved under {save_under}.")

# ---------------------------------------------------------------------------
# Input 2 — subreddit name → add directly
# ---------------------------------------------------------------------------

with right:
    st.subheader("Add a subreddit")
    st.caption(
        "Know the community already? Type it in. The page works out which stock "
        "it belongs to from its name and description; if it isn't about one stock "
        "(r/wallstreetbets, r/space) it goes on the general list."
    )
    with st.form("add_form", clear_on_submit=True):
        name = st.text_input("Subreddit", placeholder="e.g. RocketLab, r/wallstreetbets or a reddit.com link")
        stock = st.selectbox("For stock", options=[_AUTO, _GENERAL] + universe_tickers)
        add = st.form_submit_button("Add subreddit", type="primary")

    if add:
        try:
            if stock == _AUTO:
                names = load_company_names()
                universe = [UniverseEntry(ticker=t, company_name=names.get(t))
                            for t in universe_tickers]
                with st.spinner("Checking which stock it belongs to…"):
                    entry, attribution = add_subreddit_auto(name, universe)
                ticker, note = attribution.ticker, attribution.reason
                shown_name = attribution.name
            else:
                ticker = None if stock == _GENERAL else stock
                entry = add_subreddit(name, ticker=ticker)
                note, shown_name = None, entry.name if entry else name.strip()
                attribution = None
        except ValueError as exc:
            st.error(str(exc))
        else:
            where = ticker or "the general list"
            if entry:
                st.success(f"Added r/{entry.name} to {where}.")
            else:
                st.info(f"r/{shown_name.removeprefix('r/')} is already on {where}.")
            if note:
                st.caption(f"Why: {note}.")
            if attribution is not None and not attribution.archive_ok:
                st.warning("The Reddit archive couldn't be reached, so only the name was "
                           "checked. If this landed in the wrong place, remove it below "
                           "and add it again with the stock picked by hand.")

# ---------------------------------------------------------------------------
# What's saved
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Saved subreddits")

entries = load_entries()
if not entries:
    st.info("Nothing saved yet.")
else:
    filter_to = st.selectbox(
        "Show", options=["All stocks", "General list"] + sorted({e.ticker for e in entries if e.ticker}),
    )
    shown = [
        e for e in entries
        if filter_to == "All stocks"
        or (filter_to == "General list" and e.ticker is None)
        or e.ticker == filter_to
    ]
    saved_df = pd.DataFrame([{
        "Stock": e.ticker or "general",
        "Subreddit": f"https://reddit.com/r/{e.name}",
        # Entries saved before the resolver existed carry no record of how.
        "Source": e.source or "not recorded",
        "Added": e.added or "",
        "Members": f"{e.subscribers:,}" if e.subscribers is not None else "",
    } for e in shown])
    st.dataframe(
        saved_df,
        hide_index=True,
        width="stretch",
        column_config={
            "Subreddit": st.column_config.LinkColumn(display_text=r"https://reddit\.com/(r/.*)"),
        },
    )
    st.caption(f"{len(shown)} of {len(entries)} subreddits · "
               f"{len({e.ticker for e in entries if e.ticker})} stocks mapped")

    with st.expander("Remove a subreddit"):
        labels = {f"{e.ticker or 'general'} · r/{e.name}": e for e in shown}
        choice = st.selectbox("Subreddit to remove", options=list(labels))
        if st.button("Remove"):
            target = labels[choice]
            if remove_entry(target.name, target.ticker):
                st.rerun()
            else:
                st.error("It was already gone.")
