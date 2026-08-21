# 06 — Manual intervention

The user's framing was *"a lot of things might need manual intervention."*
That is not a limitation to apologize for — it is a design input. The highest
value signal in this system is frequently the least automatable:

- A JD that only exists behind a login, or on a referral page.
- What a friend inside the company says about the team's real roadmap.
- A conference talk with no transcript.
- A recruiter's phrasing of what they're screening for.
- My own read on a posting after actually thinking about it.

A system that treats these as exceptions makes them second-class and they
never get entered. So: **manual input is an adapter** (ADR-0006). It flows
through the same raw store, the same normalize step, the same extraction, and
the same scoring as an automated fetch. It differs in `source.adapter` and
nothing else.

## Path 1 — the inbox

Drop a file in `manual/inbox/`. Any of:

```
manual/inbox/
  netflix-senior-swe-media-2026-08-21.md
  reddit-coffee-chat-notes.md
  nvidia-gtc-talk-transcript.txt
```

Front-matter names the company and kind; everything below is the content:

```markdown
---
company: netflix
kind: job_posting        # or note | talk | blog_post
title: Senior Software Engineer, Media Systems
url: https://jobs.netflix.com/jobs/123456
published_at: 2026-08-14
confidence: high         # how much I trust this source
---

We are looking for an engineer to...
```

`career ingest --manual` hashes each file, stores it in the raw store exactly
like a fetched payload, moves it to `manual/processed/<date>/`, and lets the
rest of the pipeline run. A re-dropped identical file is a no-op, because
content addressing does not care where bytes came from.

## Path 2 — annotations

Any row in the database can carry a note:

```bash
career note company netflix "Rewriting the playback control plane per M. — 2026-08"
career note posting 4471   "Level looks like staff despite the 'Senior' title"
career note skill  design.systems.consistency "My Dynamo work is closer than I credit"
career note gap    892 --dismiss "Not chasing this; leading with reliability instead"
```

`--pin` makes a note appear verbatim in every brief for that entity.
**Annotations are never summarized by the LLM** — a human sentence about a
company survives into the output word for word, because paraphrasing my own
intel back to me destroys its value.

## Path 3 — overrides

Sometimes the model is wrong and I know better. Overrides live in
`config/overrides.yaml`, are applied *after* scoring, and are always visible
in output:

```yaml
skill_supply:
  - skill: design.systems.consistency
    set_supply: 70
    reason: "Ledger reconciliation work is stronger evidence than the resume shows"

demand:
  - company: netflix
    skill: domain.video
    multiply: 1.4
    reason: "Every conversation with them is about encoding. Under-weighted by text."

suppress:
  - company: google
    skill: craft.cpp
    reason: "Not going down this road"
```

Design rule: **overrides adjust, they never delete.** A suppressed row still
exists and still appears in `career gaps --show-suppressed`, with the reason
attached. A system that lets me hide inconvenient results silently would
eventually only tell me what I want to hear — which is the specific failure
mode a career tool must not have.

## Path 4 — taxonomy curation

`career taxonomy review` (see `docs/04-skill-taxonomy.md`) is the recurring
manual loop. Roughly monthly, 10 minutes: look at unmapped phrases, promote
the real ones, ignore the noise. This is the mechanism by which my vocabulary
tracks the industry instead of freezing at whatever I knew when I built this.

## Path 5 — the profile

`profile/resume.yaml` is entirely hand-maintained (ADR-0008). Nothing writes
to it. When the gap report says "no evidence for X," the fix is to go do X and
then add the evidence row — or to realize I *had* done X and never wrote it
down, which is itself a common and valuable outcome.

## Review cadence

| Cadence | Action | Time |
|---|---|---|
| Daily (automated) | ingest, extract, analyze | 0 |
| Weekly | read the diff; drop anything interesting into the inbox | 10 min |
| Monthly | taxonomy review; update prep item statuses | 30 min |
| Quarterly | update `resume.yaml` evidence; re-check `closability` priors | 1 hr |

If the weekly step stops happening, the system is not earning its keep and
should be cut down, not propped up.
