# `src/` — all the logic

Four Python packages. Everything that *thinks* lives here; the files at the
repository root (`app.py`, `pages/`) only *display*.

New here? Read [docs/start-here/03-tour-of-the-repo.md](../docs/start-here/03-tour-of-the-repo.md)
first.

---

## The four packages

| Package | One line | Status |
|---|---|---|
| [`casino_dashboard/`](casino_dashboard/README.md) | **The product** — the dashboard, its data, its database, its signals | Live |
| [`core/`](core/README.md) | Shared plumbing everything else imports | Live |
| [`fintwit/`](fintwit/README.md) | Independent tweet-archiving pipeline | Live, separate |
| [`ticker_digest/`](ticker_digest/README.md) | The original YouTube-summarising idea | Placeholder |

## How they depend on each other

```
        app.py, pages/            scripts/          .github/workflows/
              │                      │                     │
              ▼                      ▼                     ▼
    ┌──────────────────┐      ┌────────────┐     ┌───────────────────┐
    │ casino_dashboard │      │  fintwit   │     │   ticker_digest   │
    └────────┬─────────┘      └─────┬──────┘     └─────────┬─────────┘
             │                      │                      │
             └──────────┬───────────┘──────────────────────┘
                        ▼
                  ┌──────────┐
                  │   core   │   ← depends on nothing in this repo
                  └──────────┘
```

Rules that keep this from turning into spaghetti:

- **`core` imports nothing else from this repo.** If you're tempted to make it
  import from `casino_dashboard`, the code belongs somewhere else.
- **`fintwit` is an island.** Its own database, its own workflows, its own
  entry points. The dashboard does not read it.
- **Arrows point one way.** No package imports something that imports it back.

## Why the names don't match the folder

The repository is `ticker-video-digest`, the installable package is
`ticker-digest`, and the product is `casino_dashboard`. Historical accident,
documented in [docs/archive/reorg-plan-v1.md](../docs/archive/reorg-plan-v1.md).
Nothing is broken.

## Running code from here

Packages under `src/` are importable because `pyproject.toml` declares
`pythonpath = ["src"]` and `./run setup` installs the project in editable mode.
So you run them as modules from the repository root, not as file paths:

```bash
python -m casino_dashboard.jobs.daily_refresh    # the daily job
python -m ticker_digest market --thesis          # the market report
```
