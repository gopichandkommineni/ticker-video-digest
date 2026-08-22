# 3. Tour of the folders

*Reading time: 8 minutes.*

The project has 10 top-level folders. This page tells you what each one is for
and — more useful — **which one to open when you want to change a specific
thing**.

Every folder also has its own `README.md`, so you can just click into it on
GitHub and get the explanation there.

---

## The map

```
ticker-video-digest/
│
├── README.md          ← the front door
├── run                ← the helper script: ./run dashboard, ./run test …
├── app.py             ← the dashboard's HOME page
├── STRATEGY.md        ← why these themes were picked (protected)
├── CLAUDE.md          ← instructions for AI coding assistants
│
├── pages/             ← the other dashboard screens (one file = one screen)
├── config/            ← hand-edited settings. Which stocks, which notes.
├── data/              ← the saved results (two database files)
├── src/               ← all the real logic
├── scripts/           ← one-off maintenance commands
├── tests/             ← automated checks
├── docs/              ← all written documentation (you are here)
├── research/          ← old experiments, kept as a record
└── .github/workflows/ ← the scheduled robots
```

---

## Folder by folder

### `app.py` and `pages/` — the screens

Streamlit (the web framework this uses) has a simple rule: `app.py` is the home
page, and **every file in `pages/` becomes another page in the sidebar**, sorted
by its number prefix.

| File | Sidebar entry |
|---|---|
| `app.py` | Home — the grid of theme cards |
| `pages/00_Sector_Heat.py` | Sector Heat |
| `pages/01_All_Tickers.py` | All Tickers |
| `pages/02_Ticker_Detail.py` | Ticker Detail |
| `pages/03_Market_Reality_Check.py` | Market Reality Check |
| `pages/05_Congress.py` | Congress |
| `pages/06_Add_Stocks.py` | Add Stocks |

(There's no `04_`. A page was removed and the others were never renumbered.
Harmless.)

These files are mostly *layout* — they fetch already-computed numbers and
arrange them on screen. The thinking happens in `src/`.

### `config/` — the knobs you turn by hand

Plain text files (YAML — a format designed to be edited by humans) that control
what the dashboard watches. **This is the folder a non-programmer changes most
often.**

| File | What it controls |
|---|---|
| `themes.yaml` | 🔒 The 12 themes and the 64 stocks. The universe. |
| `manual_notes.yaml` | Your own catalyst / red-flag note per stock |
| `deal_log.yaml` | Big deals and contracts you've spotted, by theme |
| `etf_mapping.yaml` | Which ETFs represent each theme (for the money-flow signal) |
| `star_traders.yaml` | Which politicians to track individually |
| `ticker_subreddits.yaml` | Which subreddits to read for each stock (auto-generated, hand-editable) |
| `ticker_company_names.yaml` | Ticker → company name cache. Purely a speed-up. |

🔒 `themes.yaml` is a **protected file** — see the bottom of this page.

### `data/` — the results

Two SQLite database files. SQLite is a whole database that lives in a single
file; nothing to install or run.

| File | Holds |
|---|---|
| `snapshots.db` | The dashboard's data: prices, signals, social mentions, congress trades. ~20 MB. |
| `fintwit.db` | The separate tweet archive. ~36 MB. |

Both are **committed into git**, which is unusual for data but deliberate: it's
how the automated job hands fresh results to the deployed dashboard. Both are
production data — read [`data/README.md`](../../data/README.md) before touching
either.

### `src/` — all the logic

Four packages. If you're reading code to understand a number on the screen,
this is where you end up.

| Package | Contains |
|---|---|
| `casino_dashboard/` | **The product.** Split into `data/` (fetching), `db/` (storing), `signals/` (calculating), `jobs/` (the scheduled work), `ui/` (display helpers). |
| `core/` | Shared plumbing: config, caching, market indicators, Reddit and X clients. Used by everything. |
| `fintwit/` | An independent pipeline archiving finance tweets. Own database, own schedules. |
| `ticker_digest/` | The original YouTube-summarising idea. A placeholder — the code exists, the feature isn't built. |

Read [`src/README.md`](../../src/README.md) for how they depend on each other.

### `scripts/` — things a human runs once

Migrations and cleanups. Not part of normal operation. Each file explains
itself at the top. Some are already-completed one-time migrations kept only for
the record.

### `tests/` — automated checks

~900 checks that the logic still behaves. Run them with `./run test`.

> **Expect 17 failures.** They were already failing before you arrived and are
> unrelated to setup — mostly tests that still assume the original 8 themes, or
> that check UI details which have since changed. Details in
> [`tests/README.md`](../../tests/README.md). What matters is that the number
> doesn't *grow* after your change.

### `docs/` — everything written down

You're in it. See [`docs/README.md`](../README.md) for the index.

### `research/` — old experiments

One-off probe scripts and their committed outputs — "does this API return
consistent results?", "can this AI model summarise tweets reliably?". A
permanent record of questions already answered. **Safe to ignore entirely**
unless you're asking one of the same questions again.

### `.github/workflows/` — the robots

Ten scheduled jobs that keep the data fresh without anyone pressing anything.
The important one is `daily_refresh.yml`. See
[`.github/workflows/README.md`](../../.github/workflows/README.md).

---

## "I want to change X — where do I go?"

| I want to… | Open this |
|---|---|
| Add or remove a stock | `config/themes.yaml` — but read [Common tasks](06-common-tasks.md) first |
| Add a note about a stock | `config/manual_notes.yaml` |
| Record a big deal or contract | `config/deal_log.yaml` |
| Change how a page looks | the matching file in `pages/` |
| Change how a number is calculated | `src/casino_dashboard/signals/` |
| Change where data comes from | `src/casino_dashboard/data/` |
| Change what the daily job does | `src/casino_dashboard/jobs/daily_refresh.py` |
| Change when the job runs | `.github/workflows/daily_refresh.yml` |
| Understand a screen's design intent | `docs/specs/` |

---

## 🔒 The two protected files

`config/themes.yaml` and `STRATEGY.md` are marked **canonical** in `CLAUDE.md`.
They encode deliberate judgement calls made over months, and they must not be
regenerated, "tidied", or overwritten by a script or an AI assistant without an
explicit instruction to do so.

Editing them by hand, on purpose, is fine — that's what they're for. Having
something rewrite them wholesale is not.

---

**Next:** [4. How the data flows →](04-how-the-data-flows.md)
