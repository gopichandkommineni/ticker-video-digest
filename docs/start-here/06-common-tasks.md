# 6. Common tasks

Recipes for the things people actually need to do. Most need no programming.

Each recipe says up front whether it's a **click**, an **edit**, or a **code
change**.

---

## Add a stock to the dashboard

There are two ways, and they behave differently.

### Option A — through the dashboard *(a click; temporary-ish)*

1. Open the dashboard and go to **Add Stocks** in the sidebar.
2. Type the ticker and pick a theme.
3. Submit. The page checks the ticker really exists, then downloads its history
   in the background. Give it a minute and refresh.

This writes into the database (`user_added_tickers`), not into
`config/themes.yaml`. It's the right choice for trying something out.

> Caveat: the dashboard's universe = `themes.yaml` **plus** whatever is in that
> table. Because `snapshots.db` is committed by the automated job, an addition
> made this way does eventually reach production — but it lives in data, not in
> the curated config, and the Add Stocks page won't let you delete
> YAML-defined tickers.

### Option B — edit the config *(an edit; permanent and reviewable)*

Open [`config/themes.yaml`](../../config/themes.yaml) and add the ticker to the
right theme's list:

```yaml
  quantum:
    display_name: "Quantum Computing"
    description: "Pre-revenue post-classical compute"
    stage: "very-early"
    speculative: true
    tickers: [IONQ, RGTI, QBTS, QUBT, ARQQ, NEWONE]   # ← added at the end
```

Rules:
- Keep it inside the square brackets, comma-separated.
- Use the exact ticker as Yahoo Finance spells it.
- A stock may appear in several themes. That's supported and intentional.

Then check it parsed, and commit:

```bash
./run check      # should now report one more stock
git add config/themes.yaml
git commit -m "Add NEWONE to quantum"
```

Its price history appears after the next automated refresh (within a few hours).

> 🔒 `themes.yaml` is a protected file. Hand-editing it deliberately is exactly
> what it's for — just never let a script or an AI assistant regenerate it.

---

## Add a note, catalyst, or red flag for a stock *(an edit)*

Open [`config/manual_notes.yaml`](../../config/manual_notes.yaml):

```yaml
RKLB:
  catalyst: "Neutron first launch expected Q3"
  red_flag: null
```

Both fields are optional — use `null` for the one you have nothing to say
about. Notes appear on the Ticker Detail page. Loaded on the next refresh.

---

## Record a deal or contract *(an edit)*

[`config/deal_log.yaml`](../../config/deal_log.yaml) feeds the "Capital Flows"
column on the Sector Heat page. Required: `date`, `sector`, `summary`.

```yaml
  - date: 2026-08-19
    sector: nuclear
    summary: "Utility signs 500MW SMR supply agreement"
    amount_usd: 1200000000     # or null if not disclosed
    deal_type: contract_award
    primary_ticker: SMR
    source_url: "https://…"
```

`sector` must exactly match a theme key from `themes.yaml` (`nuclear`,
`quantum`, `drones_defense`, …). Valid `deal_type` values are listed in the
comments at the top of the file.

---

## Add a whole new theme *(an edit)*

Add a block to `config/themes.yaml`, matching the shape of the existing ones:

```yaml
  my_new_theme:
    display_name: "Human-Readable Name"
    description: "One line on why this theme exists"
    stage: "early"           # early | early-mid | mid | mid-late
    speculative: true        # true = could go to zero
    tickers: [AAA, BBB]
```

Then also add the theme to [`config/etf_mapping.yaml`](../../config/etf_mapping.yaml)
if there's an ETF that represents it — otherwise its money-flow column shows
"n/a", which is fine and already happens for Photonics.

---

## Change when the automated refresh runs *(an edit)*

In [`.github/workflows/daily_refresh.yml`](../../.github/workflows/daily_refresh.yml):

```yaml
  schedule:
    - cron: "0 13 * * 1-5"   # 9am ET
```

Times are **UTC**. Use [crontab.guru](https://crontab.guru) to check any
expression before committing it. Remember US Eastern shifts by an hour with
daylight saving; UTC does not.

---

## Run the data refresh yourself *(a command)*

Normally you never need to — GitHub does it four times a day. If you want to
test a change to the job:

```bash
./run refresh
```

This copies the production database to `data/local-test.db` and writes
**there**, leaving the real file alone. It calls live websites and takes several
minutes. `data/local-test.db` is git-ignored.

To force a refresh in production instead: GitHub → **Actions** → *Daily Refresh*
→ **Run workflow**.

---

## Read what YouTube is saying about a stock *(a command)*

```bash
./run digest RKLB
```

This finds recent YouTube videos about the stock, reads their subtitles, and
prints a short thread of what commentators said — with each point marked **NEW**,
**DEVELOPING** or **KNOWN**, and a link that jumps to the exact second of video
it came from.

"New" is compared against digests you ran before, so the first run for a stock
marks everything new and the second one starts being useful.

If you already trust a particular YouTube channel, name it instead of searching:

```bash
./run digest RKLB --channel "@spaceinvesting"
```

Every digest is saved. To re-read them without paying for the AI again:

```bash
./run threads --ticker RKLB      # list them
./run threads --show 4f2a91c0d3b7   # print one
```

This needs two API keys in `.env` (`YOUTUBE_API_KEY` and `ANTHROPIC_API_KEY` —
see *Add an API key* below), makes AI calls that cost a small amount of money,
and takes a minute or two. Nothing it prints is investment advice.

---

## Change how something looks on a page *(a code change)*

Find the page in `pages/` — the filename matches the sidebar entry. Streamlit
pages read top to bottom like a recipe, so the order of the code is the order of
the screen.

While editing, run `./run dashboard` and leave it open: saving the file reloads
the page automatically.

> The project's own non-negotiable rule: **always open the page locally before
> merging a UI change.** Passing tests are not evidence that a screen looks
> right.

---

## Change how a number is calculated *(a code change)*

1. `src/casino_dashboard/signals/computers.py` — the maths for one stock.
2. `src/casino_dashboard/signals/orchestrator.py` — runs it across all stocks.
3. `src/casino_dashboard/signals/sector_aggregator.py` — rolls stocks up to
   themes.
4. Add or update a test in `tests/`, then `./run test`.

Old values already in the database aren't retroactively recalculated — the next
refresh writes new ones.

---

## Run the checks before you commit *(a command)*

```bash
./run test
```

**17 failures are expected** — they predate you. See
[`tests/README.md`](../../tests/README.md) for the list. What matters is that
the number doesn't go *up*.

---

## Look inside the database *(a command)*

```bash
sqlite3 data/snapshots.db ".tables"
sqlite3 data/snapshots.db "SELECT * FROM signals LIMIT 5;"
```

`sqlite3` ships with macOS. For clicking around instead of typing SQL, use the
free [DB Browser for SQLite](https://sqlitebrowser.org/).

Reading is completely safe. Don't write.

---

## Add an API key *(an edit)*

```bash
cp .env.example .env      # first time only
```

Then open `.env`, paste the key after the `=`, save, and restart the dashboard.
Never commit that file. The full list of supported keys and what each unlocks
is in [`.env.example`](../../.env.example).

For production, the same key goes to GitHub → **Settings** → **Secrets and
variables** → **Actions**.

---

**Next:** [7. When things break →](07-when-things-break.md)
