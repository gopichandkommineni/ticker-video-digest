# Casino-Coherent Momentum Dashboard — Project Context

**Purpose of this document:** Hand-off context for resuming work in a new conversation. Captures what's built, what's decided, what's open, and the project's current direction. Intended for both human reference and to give a fresh AI assistant enough grounding to be useful immediately.

**Last updated:** 2026-05-06
**Repo:** github.com/gopichandkommineni/ticker-video-digest
**Live deployment:** Streamlit Cloud (URL in repo settings)

---

## 1. What this project is

A personal stock dashboard built around a "casino-coherent momentum" investment thesis: track a curated universe of stocks across thematic sectors, surface signals indicating a stock is setting up for a meaningful move, and contextualize those signals with broader-market reality.

The dashboard is **personal/small-team use**, not a commercial product. Built by gopichandkommineni (AG), an SDE based in Bellevue WA, in personal time outside primary work.

Key working principles, established through this project's history:
- **Decisions go in markdown specs in the repo.** Code is throwaway; specs survive.
- **Verify before declaring something done.** Tests pass ≠ working in production. Local `streamlit run` is a non-negotiable check before merging UI changes.
- **Don't build at the end of long sessions.** Quality drops sharply past ~hour 8 of focused work. Polish is the work that most needs fresh eyes.
- **Push back on AI-generated polish that contradicts deliberate decisions.** The spec is the contract; mockups don't override it.

---

## 2. Current state — what's built and working in production

### Data layer (production-stable)

- **Universe:** 54 hand-curated tickers across 8 sectors, defined in `config/themes.yaml`:
  - nuclear (10): SMR, OKLO, NNE, BWXT, NXE, CCJ, UEC, UUUU, DNN, LEU
  - photonics (7): LITE, COHR, AAOI, POET, FN, MRVL, CIEN
  - quantum (5): IONQ, RGTI, QBTS, QUBT, ARQQ
  - drones_defense (6): KTOS, AVAV, ONDS, RCAT, UMAC, RKLB
  - space (6): RKLB, ASTS, PL, IRDM, INTU, LUNR
  - critical_minerals (7): MP, USAR, CDE, AG, NB, UAMY, REMX
  - ai_infrastructure (8): VRT, ETN, PWR, SMCI, ANET, DELL, NTAP, POWL
  - crypto_equities (6): COIN, CRCL, BMNR, BTBT, CIFR, IREN

- **Database:** SQLite at `data/snapshots.db`, committed to main branch. Tables:
  - `ticker_snapshots` — daily OHLCV per ticker (~500 days history)
  - `signals` — long-format computed signals
  - `news_items` — recent news per ticker
  - `social_mentions` — ApeWisdom mention data
  - `ticker_metadata` — 15 fields per ticker per day (52w high/low, short %, analyst target, ownership, market cap, revenue TTM, revenue YoY, profit margin, beta, earnings dates including BMO/AMC classification)
  - `manual_notes` — one row per ticker (catalyst, red_flag, free-text from `config/manual_notes.yaml`)

- **Daily refresh:** GitHub Actions cron at 13:00 UTC. Pulls yfinance + ApeWisdom + metadata, computes signals, commits SQLite back to main. Includes lxml dependency (required for yfinance earnings_dates parsing — silent failure mode if missing). Streamlit Cloud auto-redeploys on push.

- **Signals computed daily (16):**
  - Returns: 1d, 5d, 20d, 1m (21d), ytd, 1y (252d)
  - Setup: dist_from_30d_high_pct, dist_from_30d_low_pct, near_breakout, near_breakdown
  - Volume: vol_ratio_30d
  - Technical: rsi_14
  - Social: apewisdom_mentions_today, apewisdom_velocity_24h

### UI layer (production, with known issues)

- **Per-ticker detail page** (`pages/02_Ticker_Detail.py`) implemented per locked spec at `docs/specs/per-ticker-page-spec-v1.md`.
- Layout: header + 3 Tier-1 tiles + 5 Tier-2 tiles + 4 Tier-3 tiles + 5-cell fundamentals strip + recent news + footer.
- Tile component, color logic, formatters, loaders all live in `src/casino_dashboard/ui/`.

### Test coverage

- **263 tests passing** across data layer (snapshots, metadata, signals, manual notes, news), UI components (color logic, formatters, tile rendering), and integration paths.
- Pre-existing pytest-mock dependency note resolved during UI PR.

---

## 3. Known bugs and limitations (unfixed as of this snapshot)

These are real, visible, and need addressing in any v2 work:

### UI bugs
- **`nan` rendered in empty Catalyst/Red Flag tiles on desktop.** Pandas reads NULL from SQLite as NaN; tile component coerces to string. Should render empty-state placeholder ("+ Add catalyst" / "+ Add concern") instead.
- **Dark mode tile backgrounds stay light.** Tile CSS uses hardcoded backgrounds; doesn't respect Streamlit theme variables. Bright white tiles on near-black page = visual break.
- **`-0.0%` sign formatting on near-zero changes.** Formatter rounds magnitude after preserving sign. Should round first, drop sign if zero.

### Architectural limitations
- **Universe is hand-curated.** 54 names. Adding/removing requires PR to `themes.yaml`. No automated discovery.
- **Manual notes editing is YAML-only.** No in-app editing UI for catalyst/red_flag (deferred to v2 in original spec).
- **No homepage redesign.** The 54-name list works at this scale; would not work at 500.
- **No sector heatmap.** Originally planned, deferred.
- **Reddit (PRAW) integration pending.** Reddit script-app has been awaiting review approval; ApeWisdom is the only social source live.
- **Catalyst/Red Flag prominence asymmetry (Tier 1 vs Tier 3) is flagged for testing but not validated.** Spec notes the POET case argues for equal prominence.

### Data limitations
- 4 of 54 tickers have no forward earnings date in yfinance (genuine data gap, not a bug).
- 2 tickers (BMNR, CRCL) have <252 days history → no return_1y. Self-resolves with time.
- Recent IPOs may have nulls for revenue_growth_yoy, profit_margin, beta.

---

## 4. Research and analysis artifacts in repo

These are non-code documents that capture decisions, findings, and open hypotheses:

- **`docs/specs/per-ticker-page-spec-v1.md`** — The locked design spec for the per-ticker page. Tile-based, breathing-room layout, no charts (use Finviz linkout), 12 tiles + fundamentals strip. Open questions documented (Catalyst/Red Flag prominence variant testing).

- **`docs/specs/rip-pattern-analysis-v1.md`** — Empirical analysis of indicators preceding "rip" events (≥50% return over 60 days). **Important caveat: only 3 of 12 requested tickers had data available in the analysis environment (AAOI, COHR, LITE — all photonics).** 17 events analyzed. Headline findings:
  - Strongest signal: ATR(14) as % of price rises pre-rip (r=+0.85). Volatility *expands* into rips, doesn't compress.
  - Counter-intuitive: RSI ~49 and MACD histogram negative the week before rip. "Quiet day" pattern.
  - Bollinger band squeeze and tight consolidation **never appeared** in any pre-rip period.
  - **Findings are hypothesis-level only.** Sample is small, single-sector, and three events are the same April 2025 sector trade. No control group. Patterns may not generalize.
  - Three named follow-ups: control-group analysis, de-overlap continuation events, expand to other 9 tickers (AMD, GLW, MU, SNDK, ARM, INTC, BE, NBIS, AEHR).

- **Spec revision notes** — captured during late-night iteration but not yet incorporated. Items proposed but not approved: tiles with variable shapes/sizes, Returns as horizontal slidable bar, fundamentals position change. Status: pending review with fresh eyes.

---

## 5. Strategic direction — where the project is heading

The project's intended evolution, based on conversations to date. Not a roadmap — a direction.

### The two-system architecture (decided)

**System A — The Dashboard.** Manual curation of sectors, themes, stocks. Data layer + indicators surface "is this stock about to rip" signals. Core product, heart of the work. **This is what currently exists.**

**System B — Discovery Service (deferred).** Automation pipeline (keyword matching → industry codes → ETF holdings → LLM classification → human review) that generates candidate stocks fitting thesis themes. Decoupled service. Outputs feed a queue; human reviews and adds to System A manually. **Not yet built. Not next priority.**

### The layered analysis architecture (proposed, not finalized)

Within System A, a layered approach to per-ticker analysis:

- **Layer 1 — Live data dashboard (built):** Indicators, signals, social, news from yfinance/ApeWisdom/etc. Refreshes daily.
- **Layer 2 — Narrative analysis (proposed):** A "Generate DD" button triggering an LLM workflow producing a comprehensive due-diligence writeup. Bull case, bear case, recent changes. Stored, displayed, refreshed on demand or on catalyst.
- **Layer 3 — Catalyst response (proposed, vague):** When a notable event occurs between scheduled refreshes, do something — could be re-running narrative analysis, alerting, or refreshing data. **Open question: is this a distinct layer or just "Layer 2 reruns when triggered"?**

Honest assessment from prior conversation: most likely truth is two layers (live + narrative-with-rerun-trigger), not three. Decision deferred.

### The broader-market reality-check dashboard (proposed, researched)

A separate dashboard layer addressing the thesis that "the market is decoupled from the real economy due to retail trader influx and unusual sentiments." Four panels:

1. **Valuation reality check** — Buffett indicator (Wilshire/GDP), Shiller P/E, Forward P/E, VIX, Mag-7 % of S&P 500
2. **Real economy state** — Yield curves (10Y-2Y, 10Y-3M), Sahm Rule, NFCI, high-yield credit spreads, jobless claims, manufacturing PMI
3. **Decoupling gauge** — S&P 500 vs. earnings/GDP/M2 divergence; composite Z-score
4. **Retail froth indicators** — Margin debt, put/call ratio, AAII bull/bear, 0DTE options %, breadth (% above 200d MA)

Plus a **regime banner** at top of every page with a single decoupling temperature reading.

Data sources: FRED API (free), yfinance (free), CBOE put/call (free), FINRA margin debt (free), AAII (free with delay). **Total cost: $0/month with end-of-day data.** Build estimate: 10-15 days of focused work for all four panels; 3 days for the Valuation + Real Economy panels alone.

Several "low-cost / high-impact" extras identified in research:
- SPX denominated in gold/bitcoin/CPI-adjusted dollars (currency-debasement reality check)
- Sector decoupling map (sector mcap / sector revenue, ranked)
- Insider buy/sell aggregate across universe (free via SEC EDGAR Form 4)
- Sector relative-strength rotation chart
- Daily LLM-summarized macro narrative coherence score (~$1-3/month)

### Hosting and tech-stack questions (unresolved)

Open question on whether to stay on Streamlit Cloud or rewrite the frontend in Next.js + React + Tailwind on Vercel. **Important honest framing: Vercel is a host, not a UI improver.** A frontend rewrite is justifiable only if Streamlit's design constraints are blocking specific things you can't work around. The dashboard's UI bugs noted above (nan rendering, dark mode, sign formatting) are implementation issues, not framework limitations — they'd exist in a Next.js rewrite too if not fixed.

If a rewrite is undertaken: backend (SQLite + Python signals + GitHub Actions) stays unchanged. Frontend becomes a Next.js static site that reads pre-rendered JSON (built daily after data refresh). $0/month on Vercel Hobby tier with no serverless functions or hosted DB.

**This decision is genuinely open and shouldn't be made tired.** Estimated cost of rewrite: 2-4 weeks of focused work that adds zero new features.

---

## 6. Open questions for the next session

The questions worth answering before any new build, in rough priority order:

1. **Frontend strategy.** Stay on Streamlit and fix what's broken? Or rewrite on Next.js? If rewriting, what specific Streamlit limitation forced it? (Don't restart UI work without a clear, named reason.)

2. **What's "perfect Layer 1"?** Multiple interpretations have been proposed in prior conversations: bug fixes only, expansion of yfinance fields (insider transactions, SMA50/200, ATR, Forward P/E, PEG), or structural redesign per spec revision notes. The user has not committed to one definition.

3. **Universe expansion approach.** Manual additions only (System A as-is)? Build the discovery service (System B)? Or a defined process for adding names manually but with research support (LLM-assisted suggestions for thesis themes)?

4. **Broader-market dashboard scope.** Build all four panels? Just Panels 1 + 2 (Valuation + Real Economy, the cheapest)? Just the regime banner + per-ticker badge (highest leverage, smallest scope)? Spec it carefully first?

5. **Layer 2 (narrative DD) feasibility.** What does "DD" mean concretely? What inputs feed the LLM (yfinance basics? SEC filings? earnings transcripts? recent news)? What's the output format? How fresh? What does it cost? These need answering before Layer 2 can be specced.

6. **Rip-pattern analysis follow-up.** Do the v2 work: control-group analysis + de-overlap + expanded universe. This requires getting the other 9 tickers' data into the system (either by adding them to themes.yaml temporarily for ingestion, or by running a one-off fetch path with broader network access).

---

## 7. Working principles for the next session

Concrete behaviors that have served this project well — worth preserving in the next conversation.

- **Spec changes go in the spec, not in patches against implementation.** When you look at production output and have new ideas, document them as proposed revisions, not as immediate code changes. Specs are durable; reactions are transient.

- **Verify before declaring done.** "Tests pass" is not "deployed correctly." "Code merged" is not "production works." A 30-second `streamlit run` after every UI PR catches the class of bug unit tests structurally cannot — see the production ImportError caused by missing loaders that all unit tests passed through.

- **Don't accept polished AI output that contradicts deliberate decisions.** If a generated mockup looks great but introduces charts when the spec says no charts, the right answer is "regenerate to match spec," not "let's revise the spec to match the mockup." This was a recurring trap.

- **Long sessions degrade decision quality.** Past hour 8, the temptation grows to ship rather than verify, to react rather than plan, to extend scope rather than close loops. The dashboard does not get worse overnight. Save the prompt, sleep, decide tomorrow.

- **Push back is part of the work, not friction.** When the AI assistant flags that a request contradicts a recent decision, or that you're about to rebuild a working thing for the third time, that's the value-add. Frictionless agreement is failure mode, not success.

- **Small artifacts > large artifacts.** Spec docs in markdown, captured decisions, research notes — these survive across sessions. Big PRs with vague scope sprawl. Prefer many small focused PRs over one comprehensive rewrite.

---

## 8. What to do FIRST in the new chat

A suggested opening to anchor a fresh conversation productively:

1. Read this document.
2. Pull the repo, look at `docs/specs/per-ticker-page-spec-v1.md`, `docs/specs/rip-pattern-analysis-v1.md`, `STRATEGY.md`, `CLAUDE.md`. Review them with fresh eyes.
3. Visit the live Streamlit Cloud URL on desktop and mobile. Note specifically what's working, what's broken, what's missing.
4. Decide on the Section 6 open questions one at a time, in priority order. Don't try to answer all six in the first hour.
5. Pick **one** thing to build. The smallest one that produces a visible deliverable. Resist the urge to plan the whole arc before shipping the next small thing.

---

## 9. What this document is NOT

- Not a complete roadmap. The strategic direction in Section 5 is intent, not commitment.
- Not a specification. Specs live in `docs/*-spec-*.md`.
- Not a substitute for reading the existing spec and analysis docs.
- Not a "here's everything decided." Open questions (Section 6) are real and should be re-evaluated, not assumed.

The goal is to give a future Claude conversation enough grounding to be useful immediately, while preserving the open questions that genuinely require fresh thought.
