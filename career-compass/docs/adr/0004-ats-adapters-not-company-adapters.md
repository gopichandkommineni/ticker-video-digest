# ADR-0004 — Adapters per ATS platform, not per company

**Status:** Accepted · 2026-08-21

## Context

The watchlist starts at four companies (Netflix, Google, Reddit, Nvidia) and
will grow — realistically to twenty or forty over a few years. Each needs job
postings pulled on a schedule.

The obvious structure is one module per company: `netflix.py`, `google.py`,
`reddit.py`. It is also the structure that guarantees this project dies,
because adding company #15 means writing module #15, and by then I have
fourteen slightly-different implementations of "paginate a job board" to keep
alive.

The relevant observation: almost no large company writes its own job board.
They buy one. Greenhouse, Lever, Ashby, SmartRecruiters, Workday, Eightfold —
a handful of platforms cover the overwhelming majority of the market, and each
exposes a public JSON endpoint, because the company's own careers page is a
JavaScript client calling exactly that endpoint.

## Decision

Adapters are written **per ATS platform**. Companies are configuration.

```yaml
# config/sources.yaml
- company: reddit
  kind: jobs
  adapter: ats.greenhouse
  config: { board: reddit }
  verified: false
```

Adding a company that uses a known platform is a YAML edit and no code. The
number of adapters tracks the number of *platforms in the market*, which is
small and grows slowly, rather than the number of companies I am interested
in, which is neither.

An escape hatch exists — `careers.custom`, driven by config-supplied JSON path
expressions — so an in-house board is still not a new module. When it truly
must be, that is a signal worth noticing: a genuinely new platform, likely
relevant to more than one company.

The invariant that keeps this honest: **no file under `src/career_compass/`
contains the string `"netflix"`.**

## Alternatives considered

- **One module per company.** Discussed above. N implementations of the same
  pagination bug.
- **A generic HTML scraper with per-company CSS selectors.** Superficially
  similar to this decision, but far more fragile: markup changes weekly, JSON
  APIs change yearly, and the JSON is the *intended* programmatic surface.
- **A commercial jobs API.** Costs money, has coverage gaps at exactly the
  senior levels I care about, and gives up the raw text that the extraction
  layer needs.

## Consequences

- Discovering which ATS a company uses is a manual step (open the careers
  page, watch the network tab). It happens once per company and is documented
  in `docs/03-ingestion-contracts.md`.
- Endpoint shapes drift. Every source ships `verified: false` and is excluded
  from analysis until a human runs `career sources verify` and confirms real
  data came back — because a silently-dead endpoint reads as "they are not
  hiring", which is the most dangerous possible wrong answer here.
- Six adapters must be written before the fourth company is fully covered.
  Front-loaded cost, flat marginal cost thereafter. That is the trade.
