# 00 — Vision

## The bet

The unit of professional differentiation is moving from **implementation** to
**design**.

For twenty years, "I am a Java engineer" or "I am a React engineer" was a
coherent, sellable identity, because turning a specification into working code
in a specific language was scarce and slow. That scarcity is collapsing. The
marginal cost of syntactically correct, idiomatic, test-covered code in an
arbitrary language is approaching zero.

What did *not* get cheaper:

- Deciding **what** to build, and what not to build.
- Choosing between two architectures when both work and one will hurt in
  three years.
- Modelling a domain so the schema doesn't fight the business.
- Designing an interface other teams can build against without a meeting.
- Knowing which failure modes are real at this company's scale and which are
  cargo cult.
- Owning an ambiguous problem across org boundaries.

Call this cluster **design competency**. The bet this repo makes is that
hiring — especially senior hiring at the companies on my list — is shifting
its weight onto that cluster, and that my preparation should shift with it.

If the bet is wrong, the system still works: the taxonomy has a `craft.*`
branch for tool proficiency, and the weights live in `config/scoring.yaml`.
**The thesis is a parameter, not an assumption baked into the code.** That is
itself a design decision (ADR-0005).

## Success criteria

This system is working if, on any given morning, it can answer these without
me doing research:

1. **"What is Netflix actually building right now?"** — a ranked list of
   themes from their last N months of engineering blog posts and open
   postings, not their marketing.
2. **"What do they keep asking for that I can't evidence?"** — gaps ranked by
   *leverage*: high demand at the target, low evidence on my side, and
   plausibly closable in the time I have.
3. **"What should I do this month?"** — three to five concrete prep items,
   each traceable back to specific documents, so I can sanity-check the
   reasoning instead of trusting a score.
4. **"What changed?"** — a weekly diff. New postings, closed postings, a theme
   appearing at two companies at once, a skill's demand rising.
5. **"What do I say in the room?"** — for a given company: the design
   vocabulary they use, the problems they've publicly written about, and the
   two or three stories from my own history that map onto them.

## Non-goals

| Not doing | Why |
|---|---|
| Auto-applying to jobs | Volume is not the constraint. Credibility is. |
| Beating anti-bot defenses | See `docs/08-legal-and-etiquette.md`. Public APIs and manual paste cover most of the signal at a fraction of the fragility. |
| Comp aggregation | Levels.fyi already does it, and it isn't what this system is for. |
| Application/recruiter tracking (v1) | An ATS-tracker is a different product. Candidate for v3. |
| Generating resume prose | The output is *what to go do*, not *how to phrase what I already did*. |

## Operating assumptions

- **I am the only user.** No multi-tenancy, no auth, no service. A local CLI,
  a scheduled job, and a small dashboard are the whole surface.
- **Volume is small.** A few dozen companies, a few thousand documents a year.
  This is emphatically not a big-data problem and the architecture should not
  pretend otherwise (ADR-0003).
- **Manual curation is expected and good.** Much of the best signal — a
  conversation with someone inside the company, a JD behind a login, a talk
  with no transcript — arrives by hand. That path must be pleasant, not
  exceptional (ADR-0006).
- **Freshness matters more than completeness.** A 2019 post about a system
  they have since replaced is actively misleading. Recency decay is
  first-class (ADR-0009).
- **The extraction layer will get better.** Models improve, prompts improve,
  the taxonomy improves. Every derived fact must be re-derivable from stored
  raw bytes without re-fetching anything (ADR-0002, ADR-0007).
