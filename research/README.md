# `research/` — experiments and their results

One-off scripts that answered a specific empirical question, plus the answers
they produced, committed so the record survives.

**Nothing here runs in production, and nothing here is imported by the
dashboard.** If you're onboarding, you can skip this folder entirely. Come back
only when you're about to ask a question someone may already have answered.

---

## The probe scripts

| Script | The question it answered |
|---|---|
| `gemini_probe.py`, `gemini_month_probe.py` | Can Google's Gemini reliably summarise ticker-bearing tweets into strict JSON, and does a 30-day run fit the free tier? |
| `groq_probe.py`, `groq_month_probe.py` | The same question, asked of Groq. |
| `fetch_options.py` | What do options chains look like for RKLB / PL / ASTS? Output: `options_data_RKLB_PL_ASTS.csv`. |

These need their own API keys (`GEMINI_API_KEY`, `GROQ_API_KEY`) and are run by
hand, from the repository root.

## The saved results — `probes/`

Each subfolder is one kind of question, and inside it one folder per dated run,
holding the raw responses plus a written `report.md` and `meta.md`.

| Folder | Question |
|---|---|
| `probes/variance/` | Do the tweet providers return the *same* data when asked the same thing twice? (A non-deterministic search index would mean the pipeline can never be sure it has everything.) |
| `probes/gemini_digest/` | Gemini's summarisation quality and cost, over 7-day and 30-day windows |
| `probes/groq_digest/` | The same, for Groq |
| `probes/subreddit_catalog/` | A dated sweep of finance subreddits — `catalog.csv` |

`probes/README.md` and each subfolder's own README explain the methodology.

The variance results are written by `scripts/run_variance.py` and committed
automatically by the `fintwit-variance.yml` workflow — so this tree is a live
output path, not a static archive. Don't restructure it without updating both.

---

## Why keep all this?

Because "we already tried that" is worth knowing, and because a probe with a
committed result is an argument you don't have to have twice. The write-ups
distilled from these runs live in
[`docs/research/`](../docs/research/) — findings there, raw material here.

## Adding a probe

1. One question, stated at the top of the script.
2. Write results to `probes/<kind>/<YYYY-MM-DD>_<subject>/`.
3. Include a `meta.md` (what was run, when, with which settings) and a
   `report.md` (what it means).
4. Add a row to the tables above.

Probes are descriptive only. They report what a data source *did*; they never
produce buy or sell signals.
