# How we build here

One idea runs through everything below:

> **Code gets written faster than it gets read.**
>
> AI assistants can produce a thousand lines in a minute. Nobody reviews a
> thousand lines carefully — they skim, approve, and hope. The bottleneck in
> this repository is not typing. It is *attention*.

So the repo is designed around the reader's attention, not the writer's speed.
Every rule here exists to keep one unit of work small enough that a person
actually reads it instead of scrolling past it.

---

## The four rules

### 1. A file does one job, in under 400 lines

If you can't say what a file is for in one sentence, it's doing two jobs.
Split it.

400 lines is roughly the point where a reader stops holding the whole file in
their head and starts grepping. Past that, nobody knows what else is in there,
so things get duplicated instead of reused.

### 2. A function fits on one screen — under 60 lines

A 250-line function is not one idea; it's fifteen, glued together, where
nobody can tell which line matters. Give each step a name and the function
becomes a table of contents.

Compare:

```python
def main():
    ...250 lines of fetching, computing, saving, error handling...
```

```python
def main():
    universe = stage_load_universe()
    stage_price_snapshots(universe)
    stage_social_mentions(universe)
    ...
```

The second version can be reviewed in ten seconds. That's the whole point.

### 3. A PR does one thing, and says which

Stack several small PRs rather than opening one big one. A reviewer who can
hold the entire change in their head gives you real feedback; a reviewer
facing 2,000 lines gives you a thumbs-up.

Especially: **never mix a move with a change.** If a commit relocates code
*and* edits it, the diff is unreadable and the edit hides inside the move. Do
the move in one PR (where the reviewer can verify "nothing but moves"), and the
behaviour change in the next.

### 4. Every folder explains itself

Each package under `src/`, and each major top-level folder, has a `README.md`
saying what's inside and where to change what. GitHub renders it when you click
the folder, so navigation costs nothing.

This is enforced: a package without a README fails the structure check.

---

## The structure guard

```bash
./run lint
```

`scripts/check_structure.py` enforces rules 1, 2 and 4 mechanically, and CI
runs it on every PR (`.github/workflows/structure.yml`).

It's a **ratchet, not a cliff**. The repo already had oversized files when the
guard was added, and they're listed in the script's `BASELINE`:

- a baseline file may **shrink** — the guard congratulates you and tells you
  which line to update
- a baseline file may **not grow**
- a **new** file over 400 lines fails immediately
- the *number* of over-long functions may go down, never up

Adding a row to `BASELINE` is not how you fix a failure. Splitting the file is.

---

## Writing code

- **Type hints on every function signature.** They're the cheapest
  documentation there is.
- **Pydantic models at every structured boundary** — anything crossing between
  subsystems or coming back from an API.
- **No secrets in code, ever.** Read from the environment; document the
  variable in `.env.example`.
- **No network calls in unit tests.** Use fixtures or mocks. A test that needs
  the internet is slow, flaky, and fails on a plane.
- **Log INFO for progress a human wants to see, DEBUG for diagnostics.**
- Name things after what they *are*, not what they're made of.
  `stage_price_snapshots` beats `process_data_2`.

## Writing docs

- A new document goes in the right `docs/` subfolder **and** gets a row in
  [`docs/README.md`](docs/README.md). A doc nobody can find isn't
  documentation.
- `docs/start-here/` is written for a **non-technical reader**: no unexplained
  jargon, copy-pasteable commands, and always say what the expected output
  looks like.
- When you change what a folder holds, update that folder's `README.md` in the
  same PR. Stale docs are worse than no docs, because they're believed.

---

## Before you open a PR

```bash
./run verify   # structure + tests + every page renders + production parity
```

That's four layers, ~90 seconds. What each one proves — and what none of them
can — is in [Verifying a change](docs/runbooks/verifying-a-change.md).

If you touched the daily job, also run it for real: `./run refresh` writes to a
throwaway database and exercises all thirteen stages against live sources.

And if you touched a screen, **open it in a browser**. That is a
non-negotiable rule in this project: passing tests tell you nothing about
whether a page looks right.

## Protected files

`config/themes.yaml` and `STRATEGY.md` are canonical. Edit them deliberately,
by hand, when you mean to. Never let a script or an AI assistant regenerate,
reformat, or "tidy" them. If a task seems to require rewriting one, stop and
ask.

## Known debt, deliberately not gated

- `ruff check` currently reports ~258 style issues. Worth fixing incrementally;
  not worth blocking PRs on today.
- 17 tests fail and have for a while — catalogued in
  [`tests/README.md`](tests/README.md). The count must not grow.
- `STRATEGY.md` describes 8 sectors; `config/themes.yaml` has 12. Both are
  canonical, so the drift is documented rather than "fixed".
