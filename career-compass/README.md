# Career Compass

A personal career intelligence system.

It tracks a watchlist of target companies, continuously ingests their **public
engineering signal** (tech blogs, job postings, conference talks, open source,
engineering-culture docs), reduces that signal into a **controlled skill
taxonomy**, and compares it against a structured, evidence-backed model of my
own experience — producing a prioritized answer to one question:

> *If I want to be a credible candidate at **X** in 6–12 months, what should I
> be working on this month, and what evidence do I need to be able to point at?*

## Why this exists

Language- and framework-level specialization is being commoditized. An LLM
writes idiomatic Go, Rust, or React on demand. What does not commoditize as
fast is **judgment**: deciding what to build, choosing between architectures
under real constraints, modelling a domain correctly, designing an API that
survives five years of change, and knowing which failure modes matter.

So this system is deliberately biased. It weights **design competencies** far
above tool proficiencies (see `config/scoring.yaml`), and its output is not
"learn Kubernetes" but "you have no evidence of having designed a system under
a multi-region consistency constraint, and three of Netflix's last six senior
JDs and two of their last ten blog posts are about exactly that."

## What it is *not*

- Not a job-application autopilot. It never applies to anything.
- Not a scraper that fights anti-bot systems. It uses public APIs and feeds,
  and treats manual copy-paste as a first-class input path (see ADR-0006).
- Not a resume generator. It tells me what's missing; I do the work.

## Second purpose: this repo is a system-design exercise

Every non-trivial decision is written down as an ADR in `docs/adr/`, with the
alternatives that were rejected and why. `docs/learning/system-design-curriculum.md`
maps each of this system's own design problems onto the canonical system-design
interview topics they mirror. Building it *is* the studying.

## Status

**Design phase.** Architecture, data model, contracts, and taxonomy are
specified. `src/career_compass/` contains typed module stubs that raise
`NotImplementedError` — they define the seams, not the behavior. Nothing
fetches anything yet.

## Where to start reading

| If you want | Read |
|---|---|
| The thesis and success criteria | `docs/00-vision.md` |
| How the pipeline is shaped | `docs/01-architecture.md` |
| The tables and why they exist | `docs/02-data-model.md` |
| How a new source gets added | `docs/03-ingestion-contracts.md` |
| The skill vocabulary (the crux) | `docs/04-skill-taxonomy.md` |
| How the gap number is computed | `docs/05-gap-scoring.md` |
| Where humans plug in | `docs/06-manual-intervention.md` |
| What gets built, in what order | `docs/07-roadmap.md` |
| What this refuses to do, legally | `docs/08-legal-and-etiquette.md` |
| The decision log | `docs/adr/` |

## Setup

```bash
uv sync
cp profile/resume.template.yaml profile/resume.yaml
$EDITOR profile/resume.yaml     # see profile/README.md
```

## Privacy

This repo is **private and must stay private**. `profile/resume.yaml`,
`data/career.db`, and `manual/` contain personal career information, salary
notes, and candid self-assessment. `.gitignore` protects the scratch paths;
it cannot protect you from making the repo public.
