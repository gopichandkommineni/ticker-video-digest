# Repository Reorganization Plan — v1

**Status:** EXECUTED (2026-08-01) on branch `claude/ticker-video-digest-structure-sm6sct`.
**Scope:** Structural cleanup only — no behavior changes, no feature work.

## Execution summary (what actually shipped)

The plan below was the proposal; execution diverged in three places once the
real coupling was traced:

1. **Shared layer landed as `src/core/`, not `market_data/`, and not folded
   into `casino_dashboard`.** `market/` and `social_media/` shared
   `config`/`cache`/`models` with the YouTube feature, so the neutral package
   holds that whole substrate (`models`, `config`, `cache`, `market/`,
   `social_media/`). Both `casino_dashboard` and `ticker_digest` import `core`.
2. **`probes/` was a live output path**, not inert — `scripts/run_variance.py`
   writes it and `fintwit-variance.yml` commits it. It moved to
   `research/probes/` with those path references updated.
3. **The `docs/` specs-vs-notes split was dropped** — it would have broken ~20
   cross-links between spec files (some already dangling) for little gain.

Result: top-level is now `config/ data/ docs/ pages/ research/ scripts/ src/
tests/`; `src/` holds `casino_dashboard`, `core`, `ticker_digest`, `fintwit`.
Full test suite unchanged (same 21 pre-existing failures, zero regressions).
The distribution/repo were **not** renamed (deferred); only `CLAUDE.md` /
`README.md` were rewritten around the dashboard.

---

*The original proposal follows, for reference.*

---

## 0. Decisions this plan is built on

Confirmed with the repo owner before writing this:

1. **Canonical identity = the dashboard.** The live product is the
   "casino-coherent" momentum dashboard. Package name, `CLAUDE.md`, and
   `README.md` should be rewritten around it. (Repo rename on GitHub deferred.)
2. **YouTube digest is still wanted.** The original `ticker_digest` YouTube
   modules (`youtube_client`, `transcripts`, `analyzer`, `cache`, `cli`'s
   `ticker` subcommand) stay and get wired back into the roadmap — they are
   currently a placeholder, not dead code to delete.
3. **FinTwit stays in-repo, but grouped.** The three flat top-level packages
   (`tweet_sources/`, `storage/`, `orchestration/`) plus `data/fintwit.db` and
   the 3 FinTwit workflows are one subsystem and should live under one
   namespace instead of scattered at the repo root.

---

## 1. What exists today (baseline)

Four product lines have accreted into one repo:

| Cluster | Location | LOC | Role |
|---|---|---|---|
| **Dashboard** (live) | `src/casino_dashboard/` | ~5.6k | The deployed Streamlit app (`app.py` + `pages/`) |
| **ticker_digest** | `src/ticker_digest/` | ~2.2k | YouTube digest (placeholder) **+** `market/` + `social_media/` (shared infra) |
| **FinTwit** | `tweet_sources/` `storage/` `orchestration/` | ~3.6k | Tweet ingestion → `data/fintwit.db` |
| **Research/probes** | root `*.py`, `probes/` | 53 MB | One-off experiments + committed run outputs |

### Cross-dependencies that must be preserved

- `pages/03_Market_Reality_Check.py` → `ticker_digest.market`
- `src/ticker_digest/cli.py` → `ticker_digest.market`
- `src/casino_dashboard/jobs/daily_refresh.py` → `ticker_digest.social_media.reddit.apewisdom_client`

**Consequence:** `market/` and `social_media/` are *shared data-source
infrastructure*, not YouTube-specific. The dashboard already imports from
`ticker_digest`. Any move must keep these three import paths working (or update
every call site in the same commit).

### Structural problems being fixed

1. Repo name (`ticker-video-digest`) ≠ package name (`ticker-digest`) ≠ product
   (`casino_dashboard`) ≠ `CLAUDE.md` (describes only the YouTube tool). A fresh
   session is actively misled.
2. `src/ticker_digest` is split-brained: placeholder YouTube code + live shared
   `market`/`social_media` code.
3. Packages live in two places: some under `src/` (`casino_dashboard`,
   `ticker_digest`), some at repo root (`orchestration`, `storage`,
   `tweet_sources`). Only the `src/` ones are declared in `pyproject.toml`.
4. Repo root is noisy: 6 loose probe scripts + a stray CSV.
5. `docs/` mixes durable specs with disposable notes.

---

## 2. Target structure

Everything importable moves under `src/`. Three clear package groups + a shared
layer. Names below are proposals; the important part is the shape.

```
src/
  casino_dashboard/        # THE PRODUCT — unchanged internals (already clean)
    data/  db/  jobs/  signals/  ui/  models.py  universe.py

  market_data/             # NEW shared layer — was ticker_digest/market + social_media
    market/                #   fred_client, indicators, reality_score, thesis
    social_media/          #   base, reddit/ (apewisdom, praw), x/

  ticker_digest/           # YouTube digest FEATURE only (still wanted, placeholder)
    youtube_client.py  transcripts.py  analyzer.py  cache.py
    models.py  cli.py  __main__.py

  fintwit/                 # NEW namespace — was orchestration/ + storage/ + tweet_sources/
    orchestration/
    storage/
    tweet_sources/

app.py                     # dashboard entrypoint (stays at root — Streamlit needs it)
pages/                     # dashboard pages (stays — Streamlit convention)

config/                    # unchanged (themes.yaml, etc. — CANONICAL, do not touch)
data/                      # snapshots.db + fintwit.db (version-controlled prod data)

scripts/                   # operational + migration scripts (unchanged)
research/                  # NEW — absorbs loose root probe scripts + probes/
  probes/                  #   (moved from repo root)
  gemini_probe.py  gemini_month_probe.py  groq_probe.py  groq_month_probe.py
  fetch_options.py  options_data_RKLB_PL_ASTS.csv

docs/
  specs/                   # durable: per-ticker-page-spec-*, project-context-v2, this plan
  notes/                   # disposable: sample.md, humanoid-stack.html, cutover plans
tests/                     # mirror the new package layout (see §4)
```

### Why `market_data/` as a separate shared layer

`market/` and `social_media/` are imported by the dashboard, the ticker_digest
CLI, *and* the daily refresh job. Leaving them under `ticker_digest` forces the
dashboard to import from a package named after a feature it doesn't use. Pulling
them into a neutral `market_data/` (or folding them straight into
`casino_dashboard/data/`) removes the confusing dependency and lets
`ticker_digest` become purely the YouTube feature.

**Alternative (simpler, fewer moves):** fold `market/` + `social_media/`
directly into `casino_dashboard/` (e.g. `casino_dashboard/market/`,
`casino_dashboard/social/`) and have the ticker_digest CLI import from there.
Decision point — see §6 Q1.

---

## 3. Move list (mechanical)

Each row = one `git mv` group + an import-path rewrite done in the *same* commit.

| # | From | To | Import rewrite |
|---|---|---|---|
| 1 | `src/ticker_digest/market/` | `src/market_data/market/` | `ticker_digest.market` → `market_data.market` (6 refs) |
| 2 | `src/ticker_digest/social_media/` | `src/market_data/social_media/` | `ticker_digest.social_media` → `market_data.social_media` (call sites: daily_refresh + internal) |
| 3 | `orchestration/` | `src/fintwit/orchestration/` | `orchestration.*` → `fintwit.orchestration.*` |
| 4 | `storage/` | `src/fintwit/storage/` | `storage.*` → `fintwit.storage.*` |
| 5 | `tweet_sources/` | `src/fintwit/tweet_sources/` | `tweet_sources.*` → `fintwit.tweet_sources.*` |
| 6 | root probe scripts + CSV | `research/` | none (scripts, not imported) |
| 7 | `probes/` | `research/probes/` | update `probes/README.md` paths |
| 8 | `docs/*` | `docs/specs/` or `docs/notes/` | none (update any cross-links) |

**Not moved:** `src/casino_dashboard/` (internals already clean), `app.py`,
`pages/`, `config/`, `data/`, `scripts/`.

---

## 4. Packaging + config changes (must ship with the moves)

1. **`pyproject.toml`**
   - `[project].name`: `ticker-digest` → `casino-dashboard`.
   - `[tool.setuptools.packages.find].include`: add `market_data*`, `fintwit*`
     (currently only `ticker_digest*`, `casino_dashboard*` — the flat FinTwit
     packages aren't declared at all today).
   - `[project.scripts]`: keep `ticker-digest = ticker_digest.cli:main`; consider
     adding a `casino-refresh` / `fintwit` console entry.
2. **`[tool.pytest.ini_options].pythonpath`** already = `["src"]`; once FinTwit is
   under `src/` its tests import cleanly without the current cwd-dependent hack.
3. **GitHub Actions** — update module paths in `fintwit-daily.yml`,
   `fintwit-backfill.yml`, `fintwit-variance.yml` (and any `python -m storage` /
   `python -m tweet_sources` invocations) to the new `fintwit.*` paths. **Verify
   `daily_refresh.yml` still resolves the moved `social_media` import.**
4. **`CLAUDE.md`** — rewrite the file-layout + "what this is" sections to describe
   the dashboard as the product, with ticker_digest and fintwit as sub-systems.
   This is the single highest-value doc change.

---

## 5. Risks & guardrails

- **`config/themes.yaml` and `STRATEGY.md` are CANONICAL** (v6 policy in
  `CLAUDE.md`). This reorg does **not** touch them.
- **`data/snapshots.db` / `data/fintwit.db` are production data** committed by
  Actions. Do **not** regenerate or commit them from a sandbox. Moves don't touch
  the DB files; only code paths that open them.
- **Streamlit Cloud deploy** reads `app.py` + `pages/` from repo root — those must
  stay at root. Import rewrites inside them must be verified with a local
  `streamlit run` before merge (project's non-negotiable check).
- **Import breakage is the main hazard.** Mitigation: each numbered move in §3 is
  its own commit, moved package + all call sites together, `pytest` green after
  each. No "big bang" commit.
- **Actions can't be tested locally.** After the FinTwit move, the workflow path
  updates need a careful read-through (and ideally a manual `workflow_dispatch`
  run) since a broken `python -m` path fails silently until the next cron.

---

## 6. Open decisions before execution

1. **`market_data/` as its own package, or fold into `casino_dashboard/`?**
   Separate layer = cleaner boundary; fold-in = fewer packages. (§2)
2. **Namespace names** — `market_data`, `fintwit` are proposals. Prefer others?
3. **Repo rename on GitHub** (`ticker-video-digest` → e.g. `casino-dashboard`) —
   in scope now, or leave the remote name and only fix package/docs?
4. **`research/` vs deleting stale probes** — keep all 53 MB of committed probe
   output, or prune old runs while moving?

---

## 7. Suggested execution order (when approved)

Phased so each step is independently verifiable and revertible:

1. **Docs-only, zero risk:** rewrite `CLAUDE.md` + `README.md` around the
   dashboard; reorganize `docs/` into `specs/` + `notes/`. (No import impact.)
2. **Root tidy:** move loose probe scripts + `probes/` into `research/`. (No
   imports — scripts only.)
3. **Shared layer:** extract `market/` + `social_media/` → `market_data/`
   (or into `casino_dashboard/`); rewrite the 3 known call sites; `pytest`.
4. **FinTwit grouping:** move the 3 packages under `src/fintwit/`; rewrite
   imports + workflow paths; `pytest` + workflow read-through.
5. **Packaging:** rename the distribution in `pyproject.toml`, fix `packages.find`,
   update console scripts.
6. **Final verify:** full `pytest`, local `streamlit run`, and a
   `workflow_dispatch` smoke of each FinTwit action.

Each phase = one PR against `claude/ticker-video-digest-structure-sm6sct`.
