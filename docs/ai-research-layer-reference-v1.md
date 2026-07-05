# AI Research Layer — Reference Architecture v1

**Status:** Reference document (not a build spec). Derived 2026-07-05.
**Purpose:** Source-of-truth map of how a production AI equity-research layer
is architected, derived by systematically interrogating a third-party
"AI analyst" platform (an ALVIS/Equibles-class product). Serves as the
reference design for this repo's future chat/DD layer.
**Provenance caveat:** Everything below comes from the platform's own
self-description under structured probing, cross-checked against observed
tool behavior where possible. Self-reports about tools and rules are
reliable (schemas are literally in the model's context); claims about
backend vendors, ingestion SLAs, and model identity are inference and
graded accordingly.

---

## 1. The five planes

```
┌──────────────────────────────────────────────────────────────┐
│ RENDERING      A2UI v0.9 declarative components (open spec) │
│                + self-fetching live cards (own data path)    │
├──────────────────────────────────────────────────────────────┤
│ INSTRUCTION    injected <<<WORKFLOW>>> playbook (1 exists)   │
│                + generic focused-vs-broad fallback           │
├──────────────────────────────────────────────────────────────┤
│ ORCHESTRATION  planner → parallel sub-agents (soft cap 7+1)  │
│                → barrier (collect briefs) → synthesis        │
├──────────────────────────────────────────────────────────────┤
│ TOOL LAYER     entity resolver → typed getters → doc store  │
│                with line addressing → derived scores        │
│                + two-tier catalog (core + find_tools)        │
├──────────────────────────────────────────────────────────────┤
│ DATA LAYER     SEC EDGAR, FINRA, FRED, CBOE, EOD prices,     │
│                IR transcripts — almost entirely free sources │
└──────────────────────────────────────────────────────────────┘
```

## 2. Data layer — sources of truth

| Feed | Primary source | Cadence / lag | Confidence |
|---|---|---|---|
| Prices (EOD only, no quotes) | Exchange EOD feed, vendor unknown | Prior close | Medium |
| 13F institutional holdings | SEC EDGAR 13F-HR | Quarterly, ~45-day lag | High |
| Insider transactions + 0–100 score | SEC EDGAR Forms 3/4/5 | 2-business-day lag, ~90d window | High |
| Filings full-text + semantic search | SEC EDGAR (10-K/Q, 8-K, 20-F, 6-K) | ~next business day | High |
| XBRL financial facts | SEC EDGAR companyfacts | On filing processing | High |
| Buybacks | 10-K/Q Item 5 + 8-K authorizations | Quarterly + ad hoc | High |
| Executive changes | 8-K Item 5.02, proxies | Per filing | High |
| Short interest + squeeze score | FINRA semi-monthly + daily short volume | 2×/month (+3–5d lag); volume T+1 | High |
| Macro (VIX, put/call, EFFR, INDPRO) | CBOE + FRED | EOD / daily / monthly | High |
| KPIs, guidance | NLP extraction from earnings releases/transcripts | Per earnings event | Medium |
| Earnings-call transcripts + audio | IR/transcript vendor (likely paid) | Per call | Medium |

**Coverage universe (behaviorally verified):** US-listed common stock +
US-listed foreign ADRs. NOT covered: private companies, OTC/pink sheets,
non-US primary listings. Entity resolution failed on a dotted ticker
(MOG.A) — resolver edge cases are a real failure mode.

**Key strategic fact:** every load-bearing source is free public
regulatory data (EDGAR, FINRA, FRED, CBOE). The product's value is
ingestion + normalization + line-addressable documents + derived scores
+ the citation contract — not licensed data. Free APIs if we ever want
this coverage: `efts.sec.gov` (EDGAR full-text search),
`data.sec.gov/api/xbrl/companyfacts` (XBRL), FINRA short files.
Equibles (AGPL, github.com/daniel3303/Equibles) open-sourced the
ingestion for all of it.

## 3. Tool layer — ~40 tools, four groups

1. **Orchestration (6):** `spawn_research_agent(name, focus)`,
   `collect_research_briefs()` (barrier), `update_plan`, `render_a2ui`,
   `find_tools`/`call_tool` (two-tier deferred tool catalog; catalog can
   advertise tools that aren't callable — catalog/runtime drift observed).
2. **Workspace (18):** tabs, notes (write/append/edit/read), filing
   reader, earnings-call transcript + audio control, full spreadsheet
   (cells/format/sheets/rows/columns). Every workspace call ENDS the
   turn — mutating/UI tools checkpoint; read-only data tools compose.
3. **Equity data (16):** one entity resolver (`get_company`) in front of
   typed getters (`get_current_price`, `get_price_history`,
   `get_institutional_holdings`, `get_insider_sentiment`,
   `get_valuation_multiples`, `get_short_interest`, `get_buybacks`,
   `get_company_kpis`, `get_guidance`, `get_earnings_call_events`,
   `get_executive_changes`, `get_financial_facts`) plus a document store
   with line addressing (`search_filings` → passages with
   `{documentId, fromLine, toLine}`; `list_company_documents`;
   `read_document_lines`).
4. **Derived scores are platform-side** (squeeze score, insider
   sentiment 0–100): the LLM reads scores, it never computes them.

Design patterns worth naming:
- **Entity resolver in front of everything** — fuzzy input → canonical id
  before any data tool runs.
- **Line-addressable documents** — the mechanism that makes citations
  enforceable and clickable.
- **Structure from tool surface** — briefs converge on
  ownership/insiders/valuation/filing/buybacks because those are the
  only five things the tools afford.

## 4. Orchestration contract

- Planner spawns parallel `Research · {Company}` sub-agents + one
  `Macro & Industry Context` agent. Soft cap: 7 companies + 1 macro,
  set by prompt guidance, not enforced by the tool.
- Sub-agent contract is a **natural-language `focus` string** that names
  the entity, enumerates what to gather, and prescribes the exact tools
  and literal search queries (`search_filings "humanoid"`). Every
  company agent gets an IDENTICAL focus so briefs line up
  column-for-column.
- Sub-agents share the full data-tool surface but have **no workspace
  and no rendering** — they return cited free-text briefs; only the
  orchestrator touches the UI (gather/render privilege separation).
- The "brief template" is emergent, not schema-enforced. (Where we
  differ: this repo's convention is pydantic models at every structured
  LLM boundary — enforce brief shape with structured outputs instead.)

## 5. Grounding contract (the most copy-worthy layer)

Quoted rules from the platform's system prompt, worth adopting nearly
verbatim:

1. **Blinding as enforcement:** "A sub-agent brief is your ONLY source
   of truth — you did not see the raw data." Figures must appear
   VERBATIM in a brief; never invent, estimate, round, or infer.
   Prior knowledge may pick entities and frame context — never supply
   numbers.
2. **Two distinct null states:** a figure no brief covered is
   "not retrieved this run"; a tool that returned no rows means "the
   platform has no such data." Never conflate; never attach an invented
   reason or date to a gap.
3. **Citation schema:** `Citation {documentId, fromLine, toLine, label,
   text}` rendered inline at the claim, never collected into a trailing
   sources list. `text` is the verbatim supported sentence (enables
   click-to-highlight in the filing).
4. **No fabricated IDs:** a citation's documentId must be a real id a
   tool returned. Figures from tools without documentIds (13F,
   multiples) are stated without a Source button. Never build an id
   from a form name/date.
5. **Table honesty:** a missing metric renders "n/a" in its cell —
   never filled from memory; keep columns honest across rows.
6. **Failed brief ≠ blank answer:** render self-fetching live cards
   anyway; one line noting the narrative wasn't retrieved.
7. **Turn shape:** announcing a step without a tool call is a dead
   turn; workspace calls end the turn; never touch the workspace
   between spawn and collect.

## 6. Instruction layer — workflows

- Exactly **one** workflow exists: "Industry Analysis," injected at
  session init as a `<<<WORKFLOW>>>` block (observed duplicated with
  variant content — evidence of dynamic prompt assembly). Anchor →
  peer set → identical-focus delegation → synthesis with a prescribed
  shape: one macro line → directional verdict → single DataTable
  head-to-head (figures + dates + direction in cells) → 2–3 deciding
  differences with inline citations → what to watch.
- Selection is **external injection**, not a model-side classifier.
  Fallback with no workflow: focused ask → direct tools this turn;
  deep/broad ask → spawn sub-agents. The dichotomy is depth/breadth,
  not subject matter.

## 7. Rendering plane

- `render_a2ui` emits A2UI v0.9 (Google's open generative-UI protocol,
  a2ui.org): declarative JSON (`createSurface` + `updateComponents`)
  against a pre-approved component catalog — the model composes vetted
  components, so no UI injection. Render failures surface as
  "This visual couldn't be displayed."
- **Self-fetching components:** cards like `StockCard` fetch their own
  live data client-side. Two data paths by design — the LLM path
  (briefs; citable; can fail) and the component path (live; never
  hallucinated because the LLM never writes those numbers).

## 8. Mapping to this repo's future chat/DD layer

| Their layer | Our equivalent | Verdict |
|---|---|---|
| EDGAR/FINRA/FRED ingestion → Postgres | GitHub Actions → snapshots.db / fintwit.db | Already built (different sources, same pattern) |
| Entity resolver | Resolve against themes.yaml + user_added_tickers | Copy |
| Typed getters | Fetchers over SQLite (get_ticker_snapshot, get_signals, search_fintwit, get_congress_trades, get_sector_heat) | Copy — build once, share between MCP server and chat |
| Line-addressable docs + Citation | Row-level provenance: (tweet_id, handle, date) / (table, ticker, date); news URLs | Copy the contract, simpler addressing |
| Derived scores platform-side | The 16 daily signals | Already built |
| AgentQL-style safe SQL | Read-only SQLite (`mode=ro`) + schema description + row caps | Copy |
| Free-text briefs via prompt template | Pydantic structured outputs (repo convention) | Deviate — schema-enforce |
| Sub-agent fan-out, 7+1 cap | Single agent loop | Skip at our scale |
| Two null states + no-fabricated-figures rules | System prompt of the chat layer | Copy nearly verbatim (§5) |
| A2UI components | st.dataframe / st.line_chart inside st.chat_message | Streamlit-native now; A2UI if a Next.js rewrite ever happens |
| Workspace plane (notes/spreadsheets/audio) | — | Skip (different product) |

**Build order (unchanged from prior discussion):**
1. MCP server over snapshots.db + fintwit.db (FastMCP, ~150 lines) —
   chat UI = existing Claude subscription, $0, first consumer of
   fintwit.db.
2. Only if the team wants in-app chat: Streamlit chat page reusing the
   same tool layer + §5 grounding prompt, per a docs/chat-spec-v1.md
   written first.

## 9. Open questions / unverified

- Price-tape vendor and filing-ingestion SLA (unverified inference).
- Model identity behind the persona (claimed "MiniMax-M3" — self-reports
  of model identity are frequently confabulated; unverified).
- A2UI component catalog beyond StockCard/DataTable/Valuation/
  Ownership/Citation (probe drafted, not yet run).
- Full enumeration of catalog/runtime tool drift (one case confirmed:
  get_exempt_offerings advertised but not callable).
