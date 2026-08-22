# `docs/specs/` — design decisions

Documents written **before** the code, recording what was going to be built and
why. This project's working principle is that code is throwaway and specs
survive — so these often explain a decision better than the code that resulted
from it.

> ⚠️ **A spec is not a description of what exists.** Some of these describe work
> that was never finished. Check the **Status** line at the top of each file
> before trusting it.

| Doc | Status | Subject |
|---|---|---|
| [per-ticker-page-spec-v2.md](per-ticker-page-spec-v2.md) | Current | The Ticker Detail screen — layout, content, and the TradingView embed |
| [per-ticker-page-spec-v1.md](per-ticker-page-spec-v1.md) | Superseded by v2 | Kept for the reasoning history |
| [ingestion-ledger-gaps-v1.md](ingestion-ledger-gaps-v1.md) | Shipped | FinTwit's day-log bookkeeping |
| [ingestion-worker-pool-v1.md](ingestion-worker-pool-v1.md) | Spec | Parallelising FinTwit ingestion |
| [pr-b-cutover-plan.md](pr-b-cutover-plan.md) | Plan | Moving production onto the worker pool |

## Dead links you'll hit

Several specs reference documents that were never written or never committed:
`sector-ranking-spec-v2.md`, `rip-pattern-analysis-v1.md`,
`ingestion-behavioral-audit-v1.md`, `chat-spec-v1.md`, `per-ticker-mockup.html`.

They're left broken on purpose. Silently deleting the references would hide the
fact that those documents were once part of the plan.

## Writing a new spec

Open with a header block, so the next reader knows in five seconds whether to
trust it:

```markdown
# Thing — Specification v1

**Date locked:** YYYY-MM-DD
**Status:** Spec for review | Shipped | Superseded by X
**Owner:**
```

Then: the problem, the decision, the reasoning, and what you explicitly chose
*not* to do. Add a row to the table above and to
[`docs/README.md`](../README.md).
