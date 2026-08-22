# `pages/` — the dashboard screens

One file here = one page in the dashboard's left-hand sidebar. That's a
Streamlit convention, not a rule this project invented: drop a `.py` file in
this folder and it appears in the sidebar automatically, ordered by its number
prefix.

The home page is [`app.py`](../app.py), at the repository root — Streamlit
requires that.

---

## The pages

| File | Sidebar name | Answers |
|---|---|---|
| `../app.py` | Home | Which themes exist, and how is each doing? |
| `00_Sector_Heat.py` | Sector Heat | Which theme is hottest, on money flow / hype / growth? |
| `01_All_Tickers.py` | All Tickers | Every stock in one sortable table |
| `02_Ticker_Detail.py` | Ticker Detail | Everything about one stock |
| `03_Market_Reality_Check.py` | Market Reality Check | Is the whole market priced above what the economy supports? |
| `05_Congress.py` | Congress | What are US politicians trading? |
| `06_Add_Stocks.py` | Add Stocks | Add a stock to the watched universe |

There's no `04_`. A page was removed and the rest were never renumbered —
harmless, and renumbering would change everyone's bookmarks.

## How a page is put together

Streamlit scripts run **top to bottom, every time the page loads**. There's no
callback wiring, no templates — the order of the code is the order of the
screen. That makes them unusually easy to read.

The typical shape:

```python
import streamlit as st
from casino_dashboard.ui.loaders import load_signals_matrix

st.set_page_config(page_title="…", layout="wide")   # must come first
st.title("…")

df = load_signals_matrix()      # read finished numbers from the database
st.dataframe(df)                # draw them
```

**Pages read, they don't compute.** The numbers were calculated hours earlier
by the daily job and are sitting in `data/snapshots.db`. If you find yourself
writing a formula in this folder, it probably belongs in
`src/casino_dashboard/signals/` instead.

The one exception is **Add Stocks**, which has to check a brand-new ticker
exists before accepting it, and so does call out to the internet.

## Editing a page

Leave `./run dashboard` running while you work — saving the file reloads the
browser automatically.

> **The project's non-negotiable rule:** open the page in a browser before
> merging a UI change. Passing tests do not tell you whether a screen looks
> right.

## Adding a page

1. Create `pages/07_My_Page.py`.
2. Start it with `st.set_page_config(...)` then `st.title(...)`.
3. Get your data from `casino_dashboard.ui.loaders`, or add a loader there.
4. Add a disclaimer if the page shows anything that looks like a
   recommendation — every screen must make clear this is not investment advice.

## Design specs

The Ticker Detail page has a written design spec explaining why it's laid out
the way it is:
[docs/specs/per-ticker-page-spec-v2.md](../docs/specs/per-ticker-page-spec-v2.md).
