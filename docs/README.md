# Documentation index

Everything written down about this project, in one list. Start at the top.

---

## 🚀 Start here — the onboarding path

Read these in order. Written for a non-technical reader; ~30 minutes total.

| # | Page | What it covers |
|---|---|---|
| 1 | [What is this thing?](start-here/01-what-is-this.md) | The product and the idea behind it, in plain English |
| 2 | [Get it running](start-here/02-get-it-running.md) | Copy-paste setup on your own laptop |
| 3 | [Tour of the folders](start-here/03-tour-of-the-repo.md) | What every folder is for, and where to change things |
| 4 | [How the data flows](start-here/04-how-the-data-flows.md) | Sources → daily job → database → screen |
| 5 | [Glossary](start-here/05-glossary.md) | Every stock-market and technical term, defined |
| 6 | [Common tasks](start-here/06-common-tasks.md) | Add a stock, add a note, change the schedule… |
| 7 | [When things break](start-here/07-when-things-break.md) | Symptom → cause → fix |

---

## 🔧 Runbooks — operating the live system

| Doc | When you need it |
|---|---|
| [Reddit data runbook](runbooks/reddit-local-runbook.md) | Anything Reddit-shaped: which subreddits map to which stock, how to pull posts, why the direct API no longer works |

The scheduled jobs themselves are documented next to the code, in
[`.github/workflows/README.md`](../.github/workflows/README.md).

---

## 📐 Specs — design decisions, written before the code

These record *why* something is built the way it is. Some describe work that
was never finished — each one states its own status at the top.

| Doc | Status | Subject |
|---|---|---|
| [Per-ticker page v2](specs/per-ticker-page-spec-v2.md) | Current | The Ticker Detail screen. Supersedes v1. |
| [Per-ticker page v1](specs/per-ticker-page-spec-v1.md) | Superseded | Kept for the reasoning history |
| [Ingestion ledger gaps v1](specs/ingestion-ledger-gaps-v1.md) | Shipped | FinTwit ingestion bookkeeping |
| [Ingestion worker pool v1](specs/ingestion-worker-pool-v1.md) | Spec | Parallelising FinTwit ingestion |
| [PR B cutover plan](specs/pr-b-cutover-plan.md) | Plan | Moving production onto the worker pool |

> Some specs link to documents that don't exist (`sector-ranking-spec-v2.md`,
> `rip-pattern-analysis-v1.md`, `ingestion-behavioral-audit-v1.md`,
> `chat-spec-v1.md`, `per-ticker-mockup.html`). Those were never written or
> never committed. The dead links are left as-is so the record stays honest.

---

## 🔬 Research — questions already investigated

Findings, not plans. Nothing here is running in production.

| Doc | Question it answers |
|---|---|
| [AI research layer reference v1](research/ai-research-layer-reference-v1.md) | How a production AI equity-research layer is architected |
| [Equibles tool research v1](research/equibles-tool-research-v1.md) | Does that platform have anything we can't replicate? |
| [Humanoid stack](research/humanoid-stack.html) | A one-off sector map (open it in a browser) |

Experiment *code* and its saved output live in
[`research/`](../research/) at the repository root, separately from these
write-ups.

---

## 📦 Archive — point-in-time snapshots

Historical. **Assume anything here is out of date**; kept because it explains
how the project got to where it is.

| Doc | What it is |
|---|---|
| [Reorg plan v1](archive/reorg-plan-v1.md) | The 2026-08 restructure that produced today's `src/` layout — and why the names are still mismatched |
| [Project context v2](archive/project-context-v2.md) | Full status snapshot, 2026-05-16 |
| [Project context v1](archive/project-context-v1.md) | Earlier snapshot, 2026-05-06 |

---

## Documents that live outside `docs/`

| File | Why it's there |
|---|---|
| [`README.md`](../README.md) | The front door — first thing anyone sees on GitHub |
| [`CONTRIBUTING.md`](../CONTRIBUTING.md) | How we build here: the size budgets, the one-thing-per-PR rule, and why |
| [`STRATEGY.md`](../STRATEGY.md) | 🔒 The investment thesis. Protected file. |
| [`CLAUDE.md`](../CLAUDE.md) | Instructions for AI coding assistants working in this repo |
| [`.env.example`](../.env.example) | Every API key the project understands, and what each unlocks |
| Folder `README.md`s | Every major folder explains itself: [`src/`](../src/README.md), [`config/`](../config/README.md), [`data/`](../data/README.md), [`pages/`](../pages/README.md), [`scripts/`](../scripts/README.md), [`tests/`](../tests/README.md), [`research/`](../research/README.md), [`.github/workflows/`](../.github/workflows/README.md) |

---

## Where to put a new document

| It is… | Put it in |
|---|---|
| Onboarding material for a newcomer | `docs/start-here/` |
| How to operate a live system | `docs/runbooks/` |
| A design decision, written before building | `docs/specs/` |
| The findings of an investigation | `docs/research/` |
| A snapshot that will be stale in a month | `docs/archive/` |
| An explanation of one folder's contents | that folder's own `README.md` |

Then add a row to this index. A document nobody can find isn't documentation.
