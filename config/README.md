# `config/` — the knobs you turn by hand

Plain text files that control what the dashboard watches and what it says.
**This is the folder a non-programmer edits most often**, and you don't need to
touch any code to change what's here.

They're written in **YAML**, a format designed for humans: indentation means
nesting, `#` starts a comment.

> ⚠️ YAML cares about spaces. Indent with **spaces, never tabs**, and match the
> indentation of the lines around you. After any edit run `./run check` — it
> will tell you immediately if the file no longer parses.

---

## The files

| File | Controls | Edited by |
|---|---|---|
| `themes.yaml` | 🔒 The 12 themes and 64 stocks — **the universe** | You, by hand |
| `manual_notes.yaml` | A catalyst / red-flag note per stock | You, by hand |
| `deal_log.yaml` | Notable deals and contracts, by theme | You, by hand |
| `etf_mapping.yaml` | Which ETFs represent each theme | You, by hand |
| `star_traders.yaml` | Which politicians to track individually | You, by hand |
| `ticker_subreddits.yaml` | Which subreddits to read per stock, plus a general list | The Subreddits page, jobs, or you |
| `ticker_company_names.yaml` | Ticker → company name cache | A job writes it; a pure speed-up |

Step-by-step recipes for each are in
[docs/start-here/06-common-tasks.md](../docs/start-here/06-common-tasks.md).

---

## 🔒 `themes.yaml` is a protected file

It defines what the entire dashboard looks at, and its contents are a set of
deliberate judgement calls made over months — not a generated list.

**The rule** (from [`CLAUDE.md`](../CLAUDE.md)): it must not be regenerated,
auto-formatted, "tidied", or overwritten by a script or an AI assistant without
an explicit instruction. **Editing it by hand, on purpose, is exactly what it's
for.**

Its shape:

```yaml
sectors:
  nuclear:                                   # the internal key — used everywhere else
    display_name: "Nuclear"                  # what users see
    description: "SMR builders + uranium fuel cycle"
    stage: "mid"                             # early | early-mid | mid | mid-late
    speculative: false                       # true = this could go to zero
    tickers: [SMR, OKLO, NNE, BWXT, …]
```

A stock may appear in several themes; that's supported on purpose (Rocket Lab
is in both Space and Defense). Sector scores are computed independently, and a
multi-tagged stock contributes to each theme it belongs to.

If you add a theme here, use the same key in `etf_mapping.yaml` and
`deal_log.yaml`.

---

## The two auto-written files

`ticker_subreddits.yaml` and `ticker_company_names.yaml` are produced by jobs,
but both are plain text you can safely hand-edit:

- **`ticker_subreddits.yaml`** — written by the **Subreddits** page (or
  `python -m casino_dashboard.jobs.subreddit_resolve`) and by the discovery
  jobs' `--save`. Each stock has a `subreddits` list; an optional `details`
  block records whether each one was added by hand (`manual`) or found by the
  company search (`resolved`), and when. A `general` section holds subreddits
  not tied to one stock. Hand edits are respected. Re-running discovery for a
  ticker replaces only that ticker's found subreddits — ones added by hand stay.
- **`ticker_company_names.yaml`** — a cache. Looking a name up costs one
  network round-trip per stock and the answer never changes, so it's saved.
  Delete a line to have it re-resolved, or run with `--refresh-names`.

Neither holds anything precious. If either were deleted, a job would rebuild
it.

---

## Where these are read

The daily refresh job loads all of them
(`src/casino_dashboard/jobs/daily_refresh.py`), via the loaders in
`src/casino_dashboard/data/`. **Changes take effect on the next refresh**, not
instantly — except `themes.yaml`, which the dashboard reads directly on every
page load through `casino_dashboard/universe.py`.

## What does *not* belong here

**API keys and passwords.** Those go in `.env` locally, and in GitHub Secrets
in production. Nothing secret is ever committed. See
[`.env.example`](../.env.example).
