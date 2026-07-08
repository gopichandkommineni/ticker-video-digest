# Equibles — Tool Research & Replicability Analysis (v1)

**Date:** 2026-07-08
**Question asked:** Does Equibles have any features or *layers* that we cannot replicate or
derive from our existing data sources?
**Repo studied:** https://github.com/daniel3303/Equibles (AGPL-3.0, self-hosted, ~171★)
**Marketing site studied:** equibles.com (the hosted "ALVIS" product)

---

## 0. TL;DR

**Your guess was correct: the open-source repo is backend data only.** It is a self-hosted
data-ingestion + storage + serving platform — "a mini Bloomberg Terminal you run in Docker."
It contains **no AI agent, no ALVIS, no Workspaces, and no earnings-call capture pipeline.**
Those live only in the hosted product at equibles.com and are *not* in the repository.

Splitting the question into the two things it actually asks:

- **Can we replicate the open-source repo's data?** Almost entirely **yes**. ~10 of its ~14
  datasets are already available to us today through the FMP and AlphaVantage MCP servers (or
  the same public APIs Equibles itself scrapes). Equibles adds no proprietary data on top of
  public sources — it re-scrapes SEC / FRED / CFTC / CBOE / FINRA / Yahoo just like we can.

- **What genuinely can't we get from our current feeds?** Four things, in descending order of
  value to *our* thesis:
  1. **USAspending.gov federal-contract awards mapped to tickers** — a real gap, directly
     relevant to our defense/space/nuclear names. Not in FMP or AlphaVantage.
  2. **Semantic + full-text search over the entire SEC filing corpus** — this is a *layer*, not
     a feed. Replicable in principle, but it's real engineering (ingest full corpus → embed →
     index), not an API call.
  3. **FDA advisory-committee (AdComm) calendar** as a catalyst feed — niche; low value for our
     universe (we're barely in biotech).
  4. **Deep SEC form coverage** — Form ADV, Form D, NPORT/N-CEN. Niche.

- **The actually-hard-to-replicate part isn't in the repo at all.** The hosted **ALVIS** agent
  (agentic research, cited answers, Workspaces that "keep researching while you're away") and
  Equibles' **proprietary earnings-call pipeline** (captured from each company's IR portal —
  audio + speaker-attributed transcript + slide deck, matched to the right quarter) are the
  genuine moat. They are closed. Notably, ALVIS *is* essentially the "Layer 2 — Generate DD"
  feature we've had as an open question (project-context §5).

---

## 1. What Equibles actually is (open-source repo)

A .NET 10 / C# platform that scrapes public financial data, stores it in **ParadeDB**
(PostgreSQL + `pg_search` full-text + `pgvector` embeddings), and exposes it three ways:

- **Web portal** (port 8080) — browse stocks, holdings, insiders, short data, macro, etc.
- **MCP server** (port 8081) — the same data as AI-callable tools (Claude/ChatGPT).
- **Worker services** — the scrapers/processors that keep the DB fresh.

Confirmed module structure (from `src/`): domain business-logic projects
(`Equibles.Sec.*`, `Equibles.Holdings.*`, `Equibles.InsiderTrading.*`, `Equibles.Finra.*`,
`Equibles.FdaCatalysts.*`, `Equibles.Media.*`), `Equibles.Search[.Abstractions]`,
`Equibles.Mcp.Server`, `Equibles.Web`, `Equibles.Worker[.Host]`, `Equibles.Migrations`.
**No agent / chat / reasoning / LLM-orchestration module exists.** Optional Ollama is used only
for producing embeddings, not for reasoning.

---

## 2. Dataset-by-dataset: can we already get it?

"Have it now" = available today via a connected MCP server or a source already in our pipeline.

| Equibles dataset | Can we get it today? | Our source |
|---|---|---|
| SEC EDGAR filings (10-K/Q, 8-K) — full text | ✅ Yes | FMP `secFilings`; SEC EDGAR direct |
| SEC XBRL financial statements | ✅ Yes | AlphaVantage `INCOME/BALANCE/CASH_FLOW`; FMP `statements` |
| 13F institutional holdings | ✅ Yes | FMP `form13F`; AlphaVantage `INSTITUTIONAL_HOLDINGS` |
| Insider trading (Forms 3/4/144) | ✅ Yes | FMP `insiderTrades`; AlphaVantage `INSIDER_TRANSACTIONS` |
| Congress trades (House + Senate) | ⚠️ Partial | FMP `senate` (House coverage thinner); or House/Senate disclosure sites direct |
| FINRA short volume / short interest / FTD | ⚠️ Partial | FINRA + SEC FTD files direct; vendors give short interest but not full daily volume/FTD |
| FRED macro (rates, CPI, GDP, yield spreads) | ✅ Yes | AlphaVantage macro suite; FRED API direct (already planned) |
| Yahoo OHLCV + technicals (SMA/RSI/MACD/BBands) | ✅ Yes | yfinance (already in pipeline); AlphaVantage technicals |
| CFTC Commitments of Traders | ✅ Yes | FMP `commitmentOfTraders` |
| CBOE VIX + put/call ratio | ✅ Yes | AlphaVantage `HISTORICAL_PUT_CALL_RATIO`; VIX via index feeds |
| **USAspending federal-contract awards → ticker** | ❌ **No** | Not in FMP/AlphaVantage. USAspending.gov API + custom entity→ticker mapping |
| **FDA AdComm meeting calendar** | ❌ **No** | Not in vendors. FDA.gov direct |
| **Form ADV / Form D / NPORT / N-CEN** | ❌ **No** (niche) | SEC direct only |
| **Semantic search over full filing corpus** | ❌ **No** (it's a layer, see §3) | Would have to build |

**Takeaway:** Equibles holds no data we can't otherwise reach — everything it has is scraped
from the same public regulators. The four ❌ rows are the only things not already one MCP call
away, and only the first two matter for us.

---

## 3. The things that are layers, not feeds (the real study material)

### 3.1 Semantic + full-text search over SEC filings — *hardest genuine capability in the repo*
Equibles doesn't just store 10-Ks; it indexes them with `pg_search` (BM25 full-text) and
`pgvector` embeddings so you can ask *"find the revenue-growth discussion in Apple's 10-K"* in
natural language. No vendor feed we have gives this — FMP hands you the filing document, not a
semantic index across the whole corpus. **Replicable in principle** (ingest filings → embed →
index in any pgvector/Elasticsearch store) but it is a build, not a fetch. This is the one piece
of the open-source repo worth actually studying rather than reproducing from an API.

### 3.2 USAspending → ticker mapping
The dataset is public, but the *value* is the entity-resolution layer that maps a contract
awardee (a legal entity name) to a listed ticker, with amounts / agency / NAICS-PSC / dates.
That mapping is the work; the raw API is free.

---

## 4. What's NOT in the repo at all (the hosted moat)

From equibles.com marketing, none of which appears in the open-source code:

- **ALVIS** — an agentic research analyst: plans the question, runs parallel agents across
  holdings/filings/prices/calls, and answers with a citation for every figure. This is a
  reasoning/orchestration layer, not data.
- **Workspaces** — persistent research state; "keeps researching while you're away," watchlists
  with an Equibles Rating, spreadsheets auto-filled with cited figures, reusable workflows.
- **Proprietary earnings-call pipeline** — captured from each company's *own* IR portal:
  earnings audio + speaker-attributed transcript + the slide deck, matched to the right quarter.
  They explicitly frame this as the compounding moat ("a dataset that grows daily and gets
  harder to replicate"). Note: the repo has an `Equibles.Media.BusinessLogic` module, but the
  README describes no audio-capture pipeline — assume the productized version is closed.

These are the genuinely non-replicable-by-fetching pieces — and they're exactly the layers a
data platform *can't* commoditize.

---

## 5. Verdict for our project

Framed against our 54-name casino-coherent momentum universe (nuclear, space, drones/defense,
critical minerals, photonics, quantum, AI-infra, crypto-equities):

**Not worth replicating** — Equibles' core data platform. We already reach ~10 of its 14
datasets through FMP + AlphaVantage without running a Postgres/Docker stack. Standing up
Equibles to get 13F/insider/CFTC/CBOE/FRED data we already have one MCP call away is negative ROI.

**Worth stealing the *idea* of, for our roadmap:**

1. **USAspending federal contracts → highest-signal gap for us.** Contract awards are hard
   catalysts for `drones_defense` (KTOS, AVAV, RCAT, UMAC), `space` (RKLB, ASTS, LUNR, INTU),
   and `nuclear` (BWXT, LEU, OKLO). None of our current feeds carry this. A small worker that
   pulls USAspending for our 54 names and surfaces new awards as a signal/catalyst is a
   contained, high-value add. **Recommend: spike this.**
2. **ALVIS ≈ our deferred "Layer 2 — Generate DD."** Equibles is a live reference design for the
   narrative-DD layer we've had as open question #5. Their answer: agent plans → reads primary
   sources (filings/calls) → answers with per-figure citations. If we build Layer 2, this is the
   shape to copy — cited, source-grounded, not free-text vibes.
3. **Semantic filing search** — only relevant if/when we build Layer 2 DD; not a standalone win
   at our 54-ticker scale.
4. **FDA AdComm + Form ADV/D/NPORT** — skip. Our universe is barely biotech; low value.

**One-line answer to the original question:** The open-source repo has *no data* we can't
already get, and only one capability worth studying (semantic filing search). The things that
truly can't be derived from our sources — ALVIS and the proprietary earnings-call capture — are
*not in the repo*; they're the closed hosted product. The single actionable gap for us is
USAspending federal-contract awards.

---

## 6. Sources
- Equibles repo README & `src/` tree — github.com/daniel3303/Equibles
- Equibles hosted product — equibles.com (Ask ALVIS / Workspaces / earnings-pipeline pages)
- Our available feeds — FMP & AlphaVantage MCP tool catalogs (this session); yfinance/ApeWisdom
  (current pipeline, project-context.md §2)
