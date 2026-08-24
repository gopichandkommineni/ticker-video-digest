# YouTube Insight Threads v2 — Corroboration, Trusted Channels, Batch Runs

**Project:** Casino-Coherent Momentum Dashboard
**Date locked:** 2026-08-24
**Status:** Spec — agreed, not yet built
**Extends:** `docs/specs/youtube-insight-threads-v1.md` (v1 still describes the
shipped pipeline; this document supersedes its *Novelty detection* and
*Storage* sections only)

---

## Why these three, in this order

Three units, built in sequence, each independently shippable:

| Unit | What it fixes | Blocks the others? |
|---|---|---|
| **1. Corroboration** | A claim four videos made is stored as one video's claim. The count is lost. | **Yes** — it changes the claim ledger's schema. Every day it waits, more data needs migrating. |
| **2. Trusted channels** | `--channel` is per-invocation. There's no way to say "these are my sources for this stock". | No |
| **3. Batch + budget** | Nothing meters YouTube quota or Anthropic spend, so running the universe is unsafe. | No, but unit 2 makes it worth having |

Decisions already taken: a ticker stays mandatory on every path — it is the
claim ledger's key, and novelty stays per-company.

---

# Unit 1 — Corroboration

## The gap

`claims_from_insights` collapses duplicates inside a batch to the first
occurrence. Three videos reporting one contract award produce one claim citing
one video. "How many independent sources said this" is the strongest novelty
signal available and it is currently discarded.

## Model change

`Claim.citation: Citation` becomes `Claim.citations: list[Citation]`.

```python
class Claim(BaseModel):
    ticker: str
    kind: ClaimKind
    text: str
    citations: list[Citation]          # was: citation
    fingerprint: str
    novelty: Novelty = "new"
    novelty_reasoning: str = ""
    related_claim: str | None = None
    newly_corroborated: bool = False   # new
    first_seen_at: datetime | None = None

    @computed_field
    @property
    def source_count(self) -> int:
        return len({c.video_id for c in self.citations})
```

`text` keeps the paraphrase from the **highest-ranked** source. Videos are
analysed in reliability order, so first-wins already means best-source-wins;
this makes that dependency explicit rather than incidental.

`Citation` itself does not change. It is the LLM-facing schema and adding
fields the model must fill is how schemas rot. Channel attribution is derived
by us at storage time from the video → channel map the run already holds.

## `newly_corroborated`

A deterministic flag, computed without a model call:

> A claim judged `known` or `developing` is **newly corroborated** when this
> run's citations include a **channel** that has never cited that claim before.

This is the case the thread should surface even though the claim isn't new:
the thesis didn't change, but the number of people saying it did. One channel
posting three videos is one source — hence channels, not videos.

## Storage change

`claims` splits into identity and evidence:

```sql
CREATE TABLE claims (
    ticker, fingerprint, kind, text,
    novelty, novelty_reasoning, related_claim,
    first_run_id, first_seen_at, last_seen_at,
    PRIMARY KEY (ticker, fingerprint)
);

CREATE TABLE claim_citations (
    ticker, fingerprint, video_id, timestamp_seconds,
    quote_paraphrase, channel_id, run_id, seen_at,
    PRIMARY KEY (ticker, fingerprint, video_id, timestamp_seconds)
);
```

`first_seen_at` keeps its `ON CONFLICT DO NOTHING` write and its meaning.
`last_seen_at` updates on every sighting — it is what makes "said again this
week" answerable. `channel_id` is what makes `newly_corroborated` recomputable
from history rather than trusted from a flag.

## Migration

A `schema_version` table, and `init_db` migrates v1 → v2 in place: create
`claim_citations`, copy the three citation columns across, rebuild `claims`
without them. No user action, no script to remember. Safe because
`data/digests.db` is personal, git-ignored, and at most a few runs old.

## Ordering — a new pure function

```python
def rank_claims(claims: list[Claim]) -> list[Claim]
```

Sort key: novelty rank, then source count descending.

| Rank | Claim |
|---|---|
| 0 | `new` |
| 1 | `developing` |
| 2 | `known` and newly corroborated |
| 3 | `known` |

The thread payload arrives pre-ranked. The model may still exercise judgement
about what deserves a post, but it no longer decides what leads — that's a
tested function, on the deterministic side of seam B.

## Thread change

Each claim in the payload carries `source_count` and `newly_corroborated`. The
prompt gains one rule: *a claim several sources newly agreed on earns a post
even when the claim itself isn't new — say plainly that the claim is old and
the agreement is what changed.*

## Tests

Batch dedupe accumulates citations rather than dropping them; `source_count`
counts distinct videos, not citations; ranking order across all four ranks;
`newly_corroborated` true for a new channel and false for the same channel
twice; citation round-trip through both tables; v1 → v2 migration preserves
`first_seen_at`; the thread prompt carries the counts.

---

# Unit 2 — Trusted channels

## Config

`config/youtube_channels.yaml`, following `star_traders.yaml`: hand-curated,
opinionated, owned by the user, never written by code.

```yaml
# YouTube channels you trust, and what you trust them about.
# Hand-curated — edit freely. Code reads this and never writes it.
channels:
  - handle: "@spaceinvesting"
    name: "Space Investing"
    tickers: [RKLB, ASTS]
    weight: 1.4
    note: "Good on launch cadence, weak on financials"
```

`handle` may be a handle, a channel id, or a URL — whatever `resolve_channel`
already accepts. `tickers` may be omitted to mean "trusted on everything".
`weight` defaults to 1.0.

## Component

`src/ticker_digest/channels.py` — a pure loader plus lookup, unit-testable
against a fixture file:

```python
def load_trusted_channels(path: Path = _DEFAULT) -> list[TrustedChannel]
def channels_for(ticker: str, ...) -> list[TrustedChannel]
```

## Integration

`DigestRequest.source_kind` gains `"trusted"`. The trusted path is the union of
`list_channel_videos` across the ticker's trusted channels, ranked together,
with `weight` applied as a multiplier on the reliability score.

`quality.score_videos` stays pure and trust-blind: it gains an optional
`weights: dict[channel_id, float]` argument. A weighted score can exceed 1.0 —
ranking is comparative, so that's fine, and it's documented rather than
clamped (clamping would silently make weights on strong videos do nothing).

CLI: `./run digest RKLB --trusted`. Explicit, never implicit — a run that
silently changed its sources because a config file existed would be a bad
surprise.

## Resolution caching

Turning `@handle` into a channel id costs a search call every run. Resolutions
cache in a `channel_resolutions` table in `digests.db`, keyed by the query
string. The config file is never written back to — auto-editing a
hand-curated file is rude, and it's how merge conflicts start.

## Tests

Loader parses the fixture; a missing file is empty, not fatal; `channels_for`
matches case-insensitively and treats a missing `tickers` list as "all";
weights multiply the score; the trusted path unions channels and drops
duplicate videos; an unresolvable trusted channel is skipped with a warning
rather than failing the run.

---

# Unit 3 — Batch runs with a budget

## The component that has to exist first

`src/ticker_digest/budget.py`. Nothing meters spend today, which is exactly why
batch is not safe to build without it.

```python
class RunBudget(BaseModel):
    max_tickers: int = 10
    max_videos_per_ticker: int = 3
    max_youtube_units: int = 2_000     # daily free quota is 10,000
    max_llm_calls: int = 100

class BudgetLedger:
    def can_afford(self, kind: str, cost: int) -> bool
    def spend(self, kind: str, cost: int) -> None
    def report(self) -> BudgetReport
```

YouTube quota is charged at its real rates — `search.list` is **100 units**,
`videos.list` and `channels.list` are 1 each — so the gateway reports what each
call cost. LLM calls are gated on count; token usage is recorded from each
response and reported, but not gated, because it can't be known before the call.

Exhaustion **stops cleanly between tickers** and reports what was and wasn't
covered. A batch that silently digests 4 of 12 tickers is worse than one that
says so.

## The job

`src/ticker_digest/jobs/batch_digest.py`, mirroring `casino_dashboard/jobs/`:

```bash
./run digest-batch --sector nuclear --limit 5
./run digest-batch --tickers RKLB,ASTS --trusted
```

## Open question: where the universe comes from

`casino_dashboard.universe.load_universe` reads `config/themes.yaml` **and**
merges user-added tickers from `snapshots.db`. `ticker_digest` importing it
would break the package rule that only `core` is shared.

**Recommendation:** a read-only `core/universe.py` exposing the YAML half —
`load_themes(path) -> dict[sector_id, list[ticker]]` — used by the batch job.
`casino_dashboard.universe` keeps its DB merge and delegates its YAML half to
`core` in a **separate** PR, so this unit can't destabilise the dashboard.
`config/themes.yaml` stays canonical and read-only either way.

## Open question: local only, or scheduled?

`data/digests.db` is git-ignored, which is what keeps your reading history out
of production data. A GitHub Action has nowhere to persist results without
committing that database — which would reverse the decision that made it
git-ignored, and put a robot in charge of your claim ledger.

**Recommendation:** local-only for now (`./run digest-batch`). Scheduling is a
separate decision that should be made on its own merits, not smuggled in as an
implementation detail of batching.

## Tests

The ledger refuses the call that would exceed a cap; quota is charged at real
rates; exhaustion stops between tickers and reports coverage; the report
distinguishes "not attempted" from "attempted and empty"; the job surfaces a
per-ticker failure without aborting the batch.

---

## Build order

1. **Unit 1** — schema change, so it goes first and alone.
2. **Unit 2** — additive; touches `sources.py` and `quality.py` signatures.
3. **Unit 3** — depends on nothing above, but is more useful after 2.

One reviewable commit each. They land on the same feature branch as v1 while
its pull request is still open, rather than three branches racing the same
schema.
