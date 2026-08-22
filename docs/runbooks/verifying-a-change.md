# Verifying a change

How to answer two different questions:

- **"Does it still work?"** — nothing is broken.
- **"Does it still work *the same*?"** — nothing changed that you didn't mean to change.

The second is the harder one, and it's the one that matters after a refactor.

---

## The short version

```bash
./run verify
```

Four checks, about 90 seconds. Everything below explains what it actually
proves — and, just as importantly, what it doesn't.

---

## The four layers

### 1. Structure guard — *is it still readable?*

```bash
./run lint
```

Files under 400 lines, functions under 60, a README per package. Fails if the
repo got worse. See [CONTRIBUTING.md](../../CONTRIBUTING.md).

### 2. Unit tests — *do the pieces still behave?*

```bash
./run test
```

~900 checks, no network. **Expect 17 failures** — they predate this suite and
are listed in [`tests/README.md`](../../tests/README.md). The number must not
grow.

Unit tests are good at "this function returns the right thing" and blind to
"the app still starts". Hence the next two layers.

### 3. Page render — *does every screen still load?*

```bash
./run test tests/test_pages_render.py
```

Runs all seven pages top to bottom in-process, against the real committed
database, and fails if any of them raises. This is the layer that catches a
refactor which moves a function, keeps every unit test green, and leaves a
screen throwing on load.

> **One known false negative.** Streamlit's test harness doesn't populate the
> page registry `st.page_link` reads, so it raises `KeyError('url_pathname')`
> on pages that use it — in the harness only; the page is fine in a browser.
> That exact string is ignored and nothing else is, so a real error still fails.

**This does not check that a page looks right.** Nothing automated does. Open
it in a browser before merging a UI change — that rule is not negotiable here.

### 4. Production parity — *does it still produce the same numbers?*

```bash
./run test -m parity
```

This is the one that answers "working as before", and it works because
`data/snapshots.db` is committed. That database was written by whichever
version of the code was live at the time, which makes it a free oracle: if
today's code disagrees with it, today's code changed something.

Two comparisons:

| Check | Asks |
|---|---|
| `test_init_db_matches_production_schema` | Would `init_db()` produce the tables and columns production actually has? |
| `test_signals_recompute_to_the_same_numbers` | Recomputing production's signals from production's stored inputs — do we get the same 1,144 numbers back? |

The signal check skips itself, rather than lying, when the newest price
snapshot is more recent than the newest signal row: recomputing would then
legitimately differ, and a green tick would be meaningless.

---

## Beyond the automated suite

Two things `./run verify` deliberately does not do, because both hit live
websites.

### Run the real pipeline

```bash
./run refresh
```

Copies production to `data/local-test.db` and runs all thirteen stages against
live sources — a few minutes. It's the only way to prove the job still works
end to end, and it's worth doing after any change to `jobs/`. Read the printed
stage table: the shape you want is a ✓ on every row, with failures only where
you're missing an API key locally.

`data/local-test.db` is git-ignored. Production is never touched.

### Open the dashboard

```bash
./run dashboard
```

Click through every page in the sidebar. Yes, actually.

---

## What "working as before" is worth

A green suite is evidence, not proof. Specifically, the suite cannot see:

- **How a page looks.** Layout, colour, ordering, readability.
- **Whether the numbers are *correct*** — only whether they're *unchanged*.
  A bug faithfully reproduced still passes parity.
- **Anything that only fails against a live API** — those are marked
  `integration` and excluded by default.
- **Whether the GitHub workflows still run.** They can't be tested locally. A
  broken `python -m` path fails silently until the next scheduled run — read
  workflow changes carefully, and use *Run workflow* to smoke one manually.

## Adding to the suite

When you fix a bug the suite didn't catch, add the check that would have caught
it. And confirm it has teeth: break the code on purpose and watch the new test
fail before you trust it green. Every test in
[`tests/test_public_api.py`](../../tests/test_public_api.py),
[`test_pages_render.py`](../../tests/test_pages_render.py) and
[`test_production_parity.py`](../../tests/test_production_parity.py) was
checked that way.
