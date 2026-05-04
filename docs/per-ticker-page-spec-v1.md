# Per-Ticker Page — Design Specification v1.0

**Project:** Casino-Coherent Momentum Dashboard
**Date locked:** 2026-05-04
**Status:** Content and layout principles complete. Ready for visual mockup phase in Claude Design.

---

## Purpose

Answer one question: *"Is this stock setting up for a meaningful move, and what's the catalyst?"*

This page is **not** a research workbench. It is **not** a Finviz competitor. Users who need detailed fundamentals, charts, or filings use the external linkout panel. The dashboard's value is signal aggregation across a curated 54-ticker universe — content surfaced here informs a decision; content that requires further analysis lives elsewhere.

---

## Design principles

- Breathing room over density (Stripe/Linear feel, not Bloomberg)
- 6-8 tiles above the fold on desktop; rest scroll into view
- Single column on mobile, same content as desktop
- Color used selectively (green/red for direction, yellow for warning, otherwise monochrome)
- Tier 1 tiles: larger, color-rich. Tier 2: standard. Tier 3: smaller, monochrome.
- No charts, candlesticks, sparklines (external tools handle that better)

---

## Page structure

### Header (always visible at top)

| Element | Content | Data source |
|---|---|---|
| Ticker symbol | Large bold | Existing |
| Company name | Medium | yfinance `Ticker.info['longName']` |
| Sector tag(s) | Pill, clickable to sector view | Existing universe |
| Current price | Large | Existing |
| 1d % change | Color-coded badge with arrow | Existing |
| External linkout pills | 7 pills: Finviz, Yahoo, Stocktwits, WSB, Reddit, SEC, TradingView (open in new tab) | Existing |

---

### Tier 1 tiles — high prominence (above fold, larger, color-rich)

These three tiles answer the central question. Most visual weight.

#### Setup tile

- Big label: `BREAKOUT` / `BREAKDOWN` / `NEUTRAL`
- Color: green / red / gray
- Subline: distance to nearest level (e.g., `0.0% from 30d high`)
- Data source: existing `near_breakout` / `near_breakdown` signals

#### Earnings tile

- Big number: days until next earnings (e.g., `3 days`)
- Subline 1: date + reporting window (e.g., `May 7, 2026 · AMC`)
- Subline 2: `87 days since last`
- Color: yellow if <7 days, gray otherwise
- Data source: yfinance `Ticker.calendar` + `Ticker.earnings_dates` (needs to be added)

#### Catalyst note tile

- Title: "Catalyst" with edit icon (pencil)
- Free-text content (1-2 sentences manually entered): e.g., `"Texas grant for AI transceiver manufacturing"`
- Empty state: `"+ Add catalyst"` placeholder (clickable to enter edit mode)
- Data source: new SQLite `manual_notes(ticker, catalyst, red_flag, updated_at)` table
- Editing: see Manual Notes Implementation section below

---

### Tier 2 tiles — medium prominence (visible on scroll, standard sizing)

#### Returns tile

- 5 rows: `1d`, `5d`, `1M`, `YTD`, `1Y`
- Each row: time period, percentage, green/red color
- Data: needs 1M, YTD, 1Y added to existing returns calculation (~1 hour)

#### Range tile

- Title: "52-Week Range"
- Current price prominently
- 52w High: price + `% from high` (red text)
- 52w Low: price + `% from low` (green text)
- Visual: thin horizontal bar showing position within range
- Data: yfinance `Ticker.info['fiftyTwoWeekHigh']`, `fiftyTwoWeekLow`

#### Social Attention tile

- Today's mentions: integer
- 24h velocity: `3.0x` with color (green if >2x)
- Top subreddit (when Reddit lands): `wallstreetbets`
- Data: existing ApeWisdom integration; Reddit pending approval

#### Volume tile

- Vol Ratio: `1.18x`
- Subline: `Today: 7.0M / 30d avg: 12.0M`
- Color: green if >1.5x, red if <0.5x, gray otherwise
- Data: existing `vol_ratio_30d` signal

#### Short Interest tile

- Big number: `13.5%` of float
- Subline: `0.95 days to cover`
- Color: yellow if >15% (squeeze territory)
- Data: yfinance `Ticker.info['shortPercentOfFloat']`, `shortRatio`

---

### Tier 3 tiles — lower prominence (smaller, monochrome, below fold)

#### RSI(14) tile

- Big number: `68`
- Subline: text label (`Approaching overbought` if 60-70, `Overbought` if >70, `Neutral` if 30-60, `Oversold` if <30)
- Data: computable from existing price history; persist as a signal (~1 hour)

#### Analyst Target tile

- Big number: target mean price (`$111.75`)
- Subline: `% upside or downside vs current` (color-coded)
- Data: yfinance `Ticker.info['targetMeanPrice']`

#### Ownership tile

- Insiders: `4.79%`
- Institutions: `64.28%`
- Recent activity: `Last 30d: 0 buys / 5 sells`
- Data: yfinance `Ticker.info['heldPercentInsiders']`, `heldPercentInstitutions`, `Ticker.insider_transactions`

#### Red Flag note tile

- Title: "Red Flag" with edit icon
- Free-text content (manually entered): e.g., `"Insider selling cluster Mar 9-19"`
- Empty state: `"+ Add concern"`
- Data: same `manual_notes` table as catalyst tile

> **Note from design conversation:** Try equal-prominence variant (promote Red Flag to Tier 1) in mockup phase. If equal feels better, flip the decision before locking final layout. Argument for promoting: in casino-thesis trading, knowing about red flags before buying is what prevents bad entries (e.g., the POET case: photonics sector hot, stock collapsing due to NDA-violation order cancellation — without prominent red flag visibility, this gets missed).

---

### Fundamentals strip — wide reference section

A horizontal strip below the tiles, before the news. Visually distinct from tiles (no rounded corners, lighter background, smaller text). Contains 5 reference values:

| Item | Format | Data source |
|---|---|---|
| Market Cap | `$13.97B` | yfinance `Ticker.info['marketCap']` |
| Revenue TTM | `$455.71M` | yfinance `Ticker.info['totalRevenue']` |
| Revenue YoY % | `+82.75%` (green if positive) | yfinance `Ticker.info['revenueGrowth']` |
| Profit Margin | `-8.39%` (red if negative) | yfinance `Ticker.info['profitMargins']` |
| Beta | `3.76` | yfinance `Ticker.info['beta']` |

Purpose: 5-item context strip. Tells reader how big, how fast growing, how profitable, how volatile. Reference data, not signal — visually de-emphasized so it doesn't compete with tiles.

---

### Footer (low prominence, scrollable below)

- **Recent News**: bullet list of 5 most recent headlines with publisher + clickable link
- **Last refresh timestamp**: `Last refresh: 2026-05-04 13:00 UTC`
- **Disclaimer**: `Not investment advice. Read STRATEGY.md for thesis.`

---

## Layout reference (desktop)

Approximate top-to-bottom layout:

```
┌────────────────────────────────────────────────────────┐
│  AAOI · Applied Optoelectronics, Inc.                  │
│  [Photonics & Optical]    $176.97  ↓ -3.6%             │
│  [Finviz][Yahoo][Stocktwits][WSB][Reddit][SEC][TV]     │
├────────────────────────────────────────────────────────┤
│ ┌──────────┐ ┌──────────┐ ┌────────────────────────┐   │
│ │  SETUP   │ │ EARNINGS │ │     CATALYST 📝        │   │
│ │ NEUTRAL  │ │  3 days  │ │ Texas grant for AI     │   │
│ │ -3.7%    │ │ May 7    │ │ transceiver mfg        │   │
│ │ from h   │ │ AMC      │ │                        │   │
│ │          │ │ 87d ago  │ │                        │   │
│ └──────────┘ └──────────┘ └────────────────────────┘   │
├────────────────────────────────────────────────────────┤
│ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ │
│ │RETURNS │ │ RANGE  │ │ SOCIAL │ │ VOLUME │ │ SHORT  │ │
│ │1d -3.6%│ │$176.97 │ │   3    │ │ 0.61x  │ │ 13.5%  │ │
│ │5d +21% │ │H:$190  │ │  3.0x  │ │7M/12M  │ │0.95DTC │ │
│ │1M +X%  │ │ -7%    │ │        │ │        │ │        │ │
│ │YTD+X%  │ │L:$12.5 │ │        │ │        │ │        │ │
│ │1Y +X%  │ │+1308%  │ │        │ │        │ │        │ │
│ └────────┘ └────────┘ └────────┘ └────────┘ └────────┘ │
├────────────────────────────────────────────────────────┤
│ ┌────────┐ ┌────────┐ ┌─────────┐ ┌──────────────────┐ │
│ │  RSI   │ │ANALYST │ │OWNERSHIP│ │  RED FLAG 📝     │ │
│ │  68    │ │$111.75 │ │Ins  4.8%│ │ Insider selling  │ │
│ │Approach│ │ -37%   │ │Inst 64% │ │ cluster Mar 9-19 │ │
│ │o-bought│ │ from   │ │0B / 5S  │ │                  │ │
│ │        │ │current │ │last 30d │ │                  │ │
│ └────────┘ └────────┘ └─────────┘ └──────────────────┘ │
├────────────────────────────────────────────────────────┤
│ FUNDAMENTALS                                           │
│ Mkt Cap   │ Revenue TTM │ Rev YoY  │ Margin │ Beta    │
│ $13.97B   │ $455.71M    │ +82.8%   │ -8.4%  │ 3.76    │
├────────────────────────────────────────────────────────┤
│ Recent News                                            │
│  • Simply Wall St — Is It Too Late...                  │
│  • Insider Monkey — AAOI Soars to All-Time High...     │
│  • IPO-Edge — AAOI Awarded $20.9M Texas Grant          │
│  ...                                                   │
├────────────────────────────────────────────────────────┤
│ Last refresh: 2026-05-04 13:00 UTC                     │
│ Not investment advice. Read STRATEGY.md.               │
└────────────────────────────────────────────────────────┘
```

This is approximate. Use as a starting point in Claude Design, not a rigid specification.

---

## Layout reference (mobile)

Same content, single column, in this order:

1. Header (compressed: ticker + name + price + 1d on one line; sector + linkouts on second line; linkouts may need horizontal scroll)
2. Setup
3. Earnings
4. Catalyst
5. Returns
6. Range
7. Social
8. Volume
9. Short Interest
10. RSI
11. Analyst Target
12. Ownership
13. Red Flag
14. Fundamentals (4×2 grid, two columns)
15. News (collapsed by default with "Show news" toggle)
16. Footer

Tile-internal layout shouldn't change much between mobile and desktop — just stacking vs. grid.

---

## Color palette guidelines

- **Green**: positive returns, breakout setup, high volume ratio, oversold RSI, % upside vs analyst target, positive YoY revenue growth
- **Red**: negative returns, breakdown setup, % downside vs analyst target, negative profit margin
- **Yellow**: earnings within 7 days, short interest >15%, RSI approaching overbought
- **Gray**: neutral states, monochrome backgrounds for non-signal content

Most tiles should be monochrome with a single colored accent (the metric value or status pill). Tier 1 tiles can use color in the title/border. **Avoid color saturation contests** — color earns attention by being rare.

Dark mode support if Streamlit allows easily; specific dark palette to be defined in mockup phase.

---

## Manual notes implementation options

This is the biggest open implementation question. Three options ranked by build effort:

### Option A — YAML file in repo (recommended for v1)

File `config/manual_notes.yaml`:

```yaml
AAOI:
  catalyst: "Texas grant for AI transceiver manufacturing"
  red_flag: null
POET:
  catalyst: null
  red_flag: "Marvell cancelled order over NDA violation"
```

Edit the file, commit, deploy. Read at refresh time. Zero edit UI work. Requires git access for editors.

### Option B — Streamlit admin page (medium effort)

A `/Admin` page with editable rows: `ticker | catalyst | red_flag | save`. Direct SQLite writes. Build cost: ~half-day.

### Option C — Inline editing on ticker detail page (highest effort)

Pencil icon on each note tile, click to edit in place, autosave. Polished UX but Streamlit form state is fiddly. Build cost: ~1 day.

**Recommendation: Option A for v1.** Migrate to B if multiple people are editing simultaneously. C only if A and B feel insufficient.

---

## Data work required before this UI can render

In rough effort order:

| # | Item | Effort | Source |
|---|---|---|---|
| 1 | 52-week high/low | ~30 min | yfinance `Ticker.info` |
| 2 | Insider/institutional ownership | ~30 min | yfinance `Ticker.info` |
| 3 | Returns: add 1M, YTD, 1Y | ~1 hour | extend existing returns calculation |
| 4 | Short interest + days-to-cover | ~1 hour | yfinance `Ticker.info` |
| 5 | Analyst target | ~1 hour | yfinance `Ticker.info` |
| 6 | RSI as a stored signal | ~1 hour | already computable, persist alongside others |
| 7 | 5 fundamentals values | ~1 hour | all from yfinance `Ticker.info` |
| 8 | Earnings date + days since last | ~2 hours | yfinance `Ticker.calendar` + `Ticker.earnings_dates` |
| 9 | Recent insider transactions count | ~2 hours | yfinance `Ticker.insider_transactions`, filter to 30d |
| 10 | Manual notes | ~half-day | new SQLite table, YAML loader, edit mechanism |

**Total: ~1.5-2 days of data work** before the new UI can render with real content for all tiles.

The data layer work and the UI work can proceed in parallel: data layer in Claude Code, UI mockups in Claude Design.

---

## What's deliberately NOT on this page

- ❌ Price chart (use Finviz/TradingView linkout)
- ❌ Technical indicators on chart (Finviz)
- ❌ Detailed insider transaction list (Finviz; we only show the count)
- ❌ Earnings transcripts
- ❌ Options chain
- ❌ Peer comparison
- ❌ Analyst rating change history (Finviz)
- ❌ Conference call schedule
- ❌ Detailed fundamentals beyond the 5 in the strip (Finviz)
- ❌ Detailed news article display (linkout is enough)

---

## Open questions deferred to mockup phase

These are taste-driven and best decided when you can see variants in Claude Design:

- **Tile shape**: rounded corners, hard edges, slight shadows, borders, no borders?
- **Tile background**: white, light gray, alternating, all same?
- **Sector tag styling**: filled pill, outlined pill, just colored text?
- **External linkout pill styling**: minimal vs visually prominent?
- **Empty states**: how does Catalyst tile look with no manual note?
- **Numbers prominence**: visual focus or supporting metrics?
- **Dark mode**: if implemented, what's the dark equivalent palette?
- **Try equal-prominence Catalyst/Red Flag variant** — flagged for testing
- **Tier 1 tile arrangement**: 3 across, or 1 large + 2 smaller?
- **Tier 2 arrangement**: 5 in a row (cramped on smaller desktops), or 4+1 with overflow?

---

## What to do with this spec

1. **Commit this document** to your repo as `docs/per-ticker-page-spec-v1.md`
2. **Open Claude Design** (claude.ai with the design model) in a separate session
3. **Paste this entire spec** as the input
4. **Ask for HTML or React mockups** of the desktop and mobile layouts
5. **Iterate visually** — try variants for the open questions above
6. **Save the chosen mockup** as `docs/per-ticker-mockup.html` (or screenshots) in the repo
7. **Build the data layer in parallel** — the 1.5-2 days of work in the Data Work section can happen alongside mockup iteration
8. **Pass spec + mockup + data layer** to Claude Code as the implementation prompt for the UI

---

## Decision log (for future reference)

Decisions made during the design conversation that shouldn't be revisited without strong reason:

- Removed price chart (use Finviz linkout instead — Finviz does it better)
- Tile-based layout, not card-based or table-based
- Breathing room density philosophy (Stripe/Linear, not Bloomberg)
- Same content on mobile as desktop, single-column stack
- Setup + Earnings + Catalyst as the prominent (Tier 1) tiles
- 5 fundamentals on a wide reference strip (not as tiles)
- Manual catalyst/red flag notes as free-text fields with manual editing
- Catalyst Tier 1, Red Flag Tier 3 (asymmetric — flagged for re-test in mockup phase)
- RSI included despite being a technical indicator (single number is low-cost)
- Short interest + days-to-cover as a single tile
- Recent insider transactions count merged into Ownership tile (not a separate tile)
- Skip P/E, Forward P/E, EPS, Debt/Equity, ROE, ROA from fundamentals strip (5 chosen are sufficient)

---

*End of spec v1.0.*
