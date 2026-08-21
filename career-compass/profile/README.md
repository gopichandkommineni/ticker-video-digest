# The profile — your side of the comparison

Everything in this directory is **hand-maintained**. Nothing in the system
writes here. See ADR-0008 for why it is shaped this way.

```
profile/
  resume.template.yaml   ← annotated empty scaffold; copy this
  resume.example.yaml    ← a filled-in FICTIONAL example, for shape only
  resume.yaml            ← yours. gitignored by default; see below.
```

```bash
cp profile/resume.template.yaml profile/resume.yaml
$EDITOR profile/resume.yaml
career profile validate     # checks every skill slug against the taxonomy
career profile show         # renders claims, and flags every one with no evidence
```

## The one idea to understand before filling this in

A claim and its evidence are separate things, and **the evidence is what
scores**.

An interview does not test what you know. It tests what you can demonstrate.
"I understand distributed consistency" and "here is the multi-region
reconciliation system I designed, why we chose read-repair over strict quorum,
and what broke in month three" are completely different assets, and only the
second one gets an offer.

So a claim rated 5 with zero evidence rows scores **low**, on purpose, and the
gap report says so in plain words. That is not the system doubting you — it is
the system finding the most common and most fixable failure: work you actually
did that you cannot currently point at. The prep item generated for that row
is `write` or `talk`, not `build`, because the work is already done and the
problem is that it is illegible.

## How to fill it in well

**Be honest about ratings.** A generous self-rating with no evidence behind it
produces a *worse* report, not a better one — it hides a real gap behind a
number. The cap in `config/scoring.yaml` (`unevidenced_rating_cap`) limits the
damage, but honesty is cheaper.

**Put the good stuff in evidence, not in the resume summary.** The evidence
ledger is meant to hold *more* than your resume does. The things that did not
fit on two pages are frequently your strongest material — the migration you
led, the design doc that changed a roadmap, the incident you ran. A resume is
already compressed and audience-tuned; this is not.

**Write the impact metric.** `impact_metric` gets a 1.3× multiplier because
numbers are what survive an interview. "Cut p99 from 900ms to 120ms across 40M
daily requests" beats "improved performance" by a lot, in the scoring and in
the room.

**Prefer `system` and `design_doc` evidence.** The weights are in
`config/scoring.yaml`: a shipped system you owned counts 1.0, a design doc
0.9, a merged PR 0.5, a completed course 0.2. That ordering is a claim about
what holds up under scrutiny, and it is roughly right.

**Set `last_used` truthfully.** Skills decay with a four-year half-life.
Distributed systems work from 2016 is worth about a quarter of the same work
from 2024, which is harsh and approximately true.

**Fill in `stories` last, and reread them before any interview.** They are the
"what do I say in the room" material, and the brief command pulls from them
directly.

## What to do when the report is discouraging

Read the **leverage** column, not the gap column. Gap says how much something
hurts; leverage says what to actually do about it. A large `domain.video` gap
against Netflix has low leverage on purpose — you do not close a domain gap by
studying, so the honest advice is to get adjacent to it or lead with something
else. That is more useful than a study plan that cannot work.

## Privacy

`profile/resume.yaml` is in `.gitignore` by default, so a mistake costs you
nothing. If you want the history — and there is real value in seeing your own
evidence ledger grow over two years — remove that line, but only while this
repo is private, and understand you are committing candid self-assessment and
possibly comp notes to git forever.
