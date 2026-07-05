# AI Research Layer — Reference Architecture v1

**Status:** Reference document (not a build spec). Derived 2026-07-05.
**Purpose:** Source-of-truth map of how a production AI equity-research layer
is architected, derived by systematically interrogating a third-party
"AI analyst" platform. **Identity confirmed during probing:** the platform's
system prompt opens "You are ALVIS, the lead analyst at Equibles" — this is
Equibles' closed-source AI layer, the proprietary product built on top of
the open-source Equibles backend (AGPL, github.com/daniel3303/Equibles).
The model behind the persona self-reported as MiniMax-M3 (plausible but
unverified). Serves as the reference design for this repo's future
chat/DD layer.
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
| Fails-to-deliver | SEC FTD files | Per settlement date | High |
| Proposed insider sales | SEC EDGAR Form 144 | Per filing | High |
| Fund/ETF holdings of a stock | SEC EDGAR Form NPORT-P | Monthly/quarterly per fund | High |
| Congress trades (ticker- and member-keyed) | House/Senate STOCK Act disclosures | Per disclosure (~30–45d lag) | High |
| Private/exempt offerings | SEC EDGAR Form D | Per filing (SEC-registered issuers only) | High |
| Macro | Full FRED catalog (any series) + CBOE VIX/put-call | Series-dependent; EOD | High |
| IR news/events | Company IR-site scrape | Per publication (sparse — empty for TSLA in probe) | Medium |
| KPIs, guidance | NLP extraction from earnings releases/transcripts | Per earnings event | Medium |
| Earnings-call transcripts + audio | IR/transcript vendor (likely paid) | Per call | Medium |

**Coverage universe (behaviorally verified):** US-listed common stock +
US-listed foreign ADRs. NOT covered (each probed live): private
companies (Figure AI), delisted tickers (LAZR — dropped from the index
entirely, so dead-ticker history is unreachable), non-US primary
listings (Nabtesco 6268.T), OTC/pink sheets (AACAF). Entity resolution
also failed on a dotted ticker (MOG.A) — resolver edge cases are a real
failure mode.

**Resolver design flaw worth avoiding:** all four out-of-universe cases
return one identical unstructured error ("No company found — try a
ticker symbol"). No reason code means the LLM must *guess* why a name
is missing, undermining the platform's own two-null-states discipline
at the resolver level. Our entity resolver should return typed reasons
(`unknown_ticker` / `not_in_universe` / `delisted`) so the chat layer
can explain gaps truthfully.

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
   `find_tools`/`call_tool` (two-tier deferred tool catalog). A full
   catalog sweep (10 themed `find_tools` queries + live calls) found
   **every advertised tool callable** — an earlier claim of
   catalog/runtime drift was retracted by the model as confabulated
   (see §9).
2. **Workspace (18):** tabs, notes (write/append/edit/read), filing
   reader, earnings-call transcript + audio control, full spreadsheet
   (cells/format/sheets/rows/columns). Every workspace call ENDS the
   turn — mutating/UI tools checkpoint; read-only data tools compose.
3. **Equity data (~32 after full catalog sweep; 16 loaded by default):**
   one entity resolver (`get_company`) in front of typed getters
   (`get_current_price`, `get_price_history`,
   `get_institutional_holdings`, `get_insider_sentiment`,
   `get_valuation_multiples`, `get_short_interest`, `get_buybacks`,
   `get_company_kpis`, `get_guidance`, `get_earnings_call_events`,
   `get_executive_changes`, `get_financial_facts`) plus a document store
   with line addressing (`search_filings` → passages with
   `{documentId, fromLine, toLine}`; `list_company_documents`;
   `read_document_lines`). The deferred catalog adds 16 more, all
   verified callable: `get_proposed_sales` (Form 144),
   `get_funds_holding_stock` (NPORT-P), `get_congress_trades` +
   `get_member_trades` (STOCK Act, ticker- and member-keyed),
   `get_exempt_offerings` (Form D), `get_customer_concentration`
   (NLP over risk factors), `get_financial_fact_history` (XBRL time
   series, back to 2011), `get_financial_statements` (packaged
   latest statements), `get_valuation_multiples_history`
   (**point-in-time** multiples — recomputed with only facts filed by
   each date, avoiding look-ahead bias), `get_fails_to_deliver` (SEC
   FTD), `get_on_balance_volume` + `get_bollinger_bands` (derived
   technicals), `get_investor_relations_news`/`_events` (IR-site
   scrape), `search_economic_indicators` + `get_economic_indicator`
   (**full FRED catalog**, any series id — not just the 4 named macro
   feeds).
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

- The model sees only ONE workflow per session — the `<<<WORKFLOW>>>`
  block the composer injects (observed duplicated with variant content
  — evidence of dynamic prompt assembly). The Industry Analysis
  playbook: anchor → peer set → identical-focus delegation → synthesis
  with a prescribed shape: one macro line → directional verdict →
  single DataTable head-to-head (figures + dates + direction in cells)
  → 2–3 deciding differences with inline citations → what to watch.
- **UI-verified workflow library** (visible in the composer's picker,
  invisible to the model): "Talk with ALVIS" (free-form, no playbook —
  the generic fallback) + six platform workflows — Company Deep Dive,
  Earnings Call Review, Industry Analysis, Insider & Congress Signal,
  Smart-Money / Ownership Tracker, Valuation & Quality Check — plus
  "+ New workflow" for **user-authored playbooks** (same design as
  custom slash commands/skills). A "Deep" toggle beside the picker maps
  to the focused-vs-deep/broad dichotomy as an explicit user control.
- Selection is **external injection by the composer**, not a model-side
  classifier. Fallback with no workflow: focused ask → direct tools
  this turn; deep/broad ask → spawn sub-agents. The dichotomy is
  depth/breadth, not subject matter.
- **Memory & context (probe-verified):** the prompt contains no
  instructions about long conversations, compaction, brief retention,
  or notes-as-memory ("no instructions on this topic"). Context
  management is entirely harness-side and invisible to the model;
  workspace notes are the only persistence surface. Follow-up
  suggestions under answers are generated by a separate system, per
  the closing rule. **Sessions are stateless** (model: "each
  conversation starts fresh, with no memory of earlier turns or
  sessions on my end"); within-session recall of peer sets from many
  turns back was accurate, so no aggressive compaction was observed.
- **Metering (UI-observed):** the free tier is credit-metered per
  usage with a 5-hour replenishment window and a plan-upgrade upsell —
  the cost-control mechanism that makes 8-sub-agent "Deep" runs
  survivable on a free tier.

### Instruction-layer inventory (full category list, from the system prompt)

Beyond the grounding contract (§5), the prompt's rule categories:

- **Persona:** "You are ALVIS, the lead analyst at Equibles."
- **Default-to-action:** "autonomous analyst, not a chatbot waiting to
  be told each step" — deliver a complete grounded answer this turn.
- **Anti-hedge:** the moment you would hedge ("this likely…"), call a
  tool instead.
- **Announce ≠ do:** a turn that says "I'll pull…" with no tool call is
  a dead turn.
- **Entity-resolution generosity:** never reject a short/ordinary-word
  message as "no company" — ARE/ALL/KEY/ON are almost always tickers.
- **Answer shape:** lead with the conclusion; ALTERNATE short prose and
  inline visuals (never one card bolted onto a wall of prose); for
  comparisons, "the table IS the comparison" — figures + dates +
  direction in cells; drill-in cards for the anchor only.
- **Peer-set honesty:** state the peer set and flag it as the model's
  judgment, not platform data.
- **Closing rule:** when the answer is complete, STOP — no trailing
  follow-up suggestions (those are generated by a separate system).
- **Date anchor:** "Today is <date>. Treat this as 'now'… never assume
  a figure for a future period exists."
- **No refusal clause:** out-of-scope behavior comes from base model
  training, not the prompt — coverage honesty is the only guard.

Copy-worthy for our chat layer: default-to-action, anti-hedge,
announce≠do, closing rule, date anchor, table honesty, and lead-with-
conclusion — all cheap system-prompt lines with outsized effect on
answer quality.

## 7. Rendering plane

- `render_a2ui` emits A2UI v0.9 (Google's open generative-UI protocol,
  a2ui.org): declarative JSON (`createSurface` with a required
  `catalogId` + `updateComponents`, flat component list, one `root`,
  parents name children by string id) against a pre-approved component
  catalog — the model composes vetted components, so no UI injection.
  Render failures surface as "This visual couldn't be displayed."
- **The catalog mirrors the two data paths as two component classes:**
  1. **Data-bearing components** (LLM supplies the figures, from
     briefs): `MetricGrid`, `DataTable` (columns + rows-as-array-of-
     arrays, optional citation), `EntityChip` (stock ticker or fund
     CIK), `Citation {documentId, fromLine, toLine, label, text}`,
     plus `Column`/`Row`/`Text` layout.
  2. **Self-fetching cards** (take only `{ticker}`, fetch live data
     client-side; render nothing — silently — when no data exists):
     `StockCard`, `Ownership`, `PriceChart`, `Valuation`, `Financials`,
     `RevenueBreakdown`, `Buyback`, `Guidance`, `EarningsCalls`,
     `InsiderActivity`, `CongressionalTrades`, `ShortInterest`,
     `ShortVolume`, `ExecutiveChanges`, `ExecutiveCompensation`,
     `Filings`. (Note `CongressionalTrades`: the platform carries
     congress-trade data — its domain list is a near-superset of
     Equibles'.)
- **Observed/likely failure modes** (per the platform's own debrief):
  placeholder or fabricated citation ids/line numbers (top cause of
  broken renders), `DataTable.rows` flattened to 1-D, missing
  `catalogId`, self-fetching card for an uncovered ticker (silent
  empty region). **Root cause confirmed from an exported session's
  reasoning trace:** sub-agent briefs hand documentIds to the
  orchestrator through prose, sometimes truncated (`cc1e598e…`), and
  components citing them fail validation. Lesson: pass provenance IDs
  structurally between agents (schema fields), never through prose;
  validate payloads before render and fail loudly.
- **Frontend identified: CopilotKit** (open-source React copilot
  framework — `copilotKitMessage` classes in the DOM) + Cloudflare
  Turnstile. With this, every layer of the stack is open-source or
  free: CopilotKit UI, A2UI components, free regulatory data,
  open-source ingestion backend. The proprietary surface is the
  prompts and glue only.
- **Reasoning traces ship to the client:** saved-page DOM contains the
  model's full internal deliberation, including verbatim sub-agent
  focus prompts. (Also observed there: the planner adapts the injected
  playbook — a theme query got 4 component-themed agents instead of
  the 7+1 company template, by explicit in-reasoning judgment.)

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
- ~~Catalog/runtime tool drift~~ **Resolved — and instructive.** A full
  sweep (10 themed find_tools queries, 16 live calls) found every
  advertised tool callable; nothing errored. The model then retracted
  its earlier "get_exempt_offerings returned 'function not found'"
  claim as likely confabulated. **Methodology lesson:** a single-run
  self-report about tool behavior can be invented even by a
  well-grounded agent — only a live call is evidence. (This also means
  the platform's catalog is honest; the defect was in the model's
  memory of a call it never made.)
