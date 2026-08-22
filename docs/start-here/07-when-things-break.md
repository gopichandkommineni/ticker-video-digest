# 7. When things break

Symptom → cause → fix. Find your symptom, follow the steps.

**Always start here:**

```bash
./run check
```

It tells you in five lines whether your machine is set up correctly.

---

## Setup problems

### `permission denied: ./run`

The script isn't marked executable. One time only:

```bash
chmod +x run
```

### `command not found: ./run`

You're in the wrong folder. Get back into the project:

```bash
cd ~/code/ticker-video-digest    # adjust the path to wherever you cloned it
ls                               # you should see README.md, app.py, src/ …
```

### `No Python environment found. Run: ./run setup`

Exactly what it says:

```bash
./run setup
```

### `./run setup` fails partway through

Usually a network hiccup or a stale half-built environment. Wipe and retry:

```bash
rm -rf .venv
./run setup
```

If it fails again, read the *last* error line — the ones above it are usually
noise. `error: Microsoft Visual C++` or `clang: error` means a library needs
compiling; on a Mac, `xcode-select --install` fixes most of those.

### `python3: command not found`

Python isn't installed. Get 3.11 or newer from
[python.org/downloads](https://www.python.org/downloads/).

---

## Dashboard problems

### It won't start — `ModuleNotFoundError: No module named 'casino_dashboard'`

The environment is missing or half-installed.

```bash
./run setup
./run dashboard
```

### The browser says "can't connect to localhost:8501"

Either the dashboard isn't running (check the Terminal window — did you press
`Ctrl+C`?), or something else is using that port:

```bash
./run dashboard --server.port 8502     # then open localhost:8502
```

### It opens but every page is empty

The database is missing or empty. Check:

```bash
./run check
```

If it reports the database missing, you probably don't have the full repository
— `data/snapshots.db` is committed to git, so a proper clone includes it:

```bash
git status data/snapshots.db
git checkout data/snapshots.db     # restore it if you deleted it
```

### The prices are days or weeks old

The dashboard is fine; the automated job stopped succeeding. Check GitHub →
**Actions** → *Daily Refresh*:

- **Red runs** — open the newest one, read which stage failed.
  An expired API key is the most common cause.
- **No runs at all** — GitHub disables scheduled workflows in repositories with
  no activity for 60 days. Push any commit, or press **Run workflow** manually.
- **Green runs, stale data** — open the run's **Summary** tab. Individual
  stages can fail while the run still passes, by design.

### One stock shows no data

Yahoo Finance doesn't recognise the ticker, or the company was delisted or
renamed. Search the ticker on finance.yahoo.com. If it's wrong, fix the spelling
in `config/themes.yaml`; if it's genuinely gone, remove it.

### A page crashes with a red Python error

Read the **last** line of the red box — that's the actual error. Then:

1. `git status` — did you edit something?
2. `git stash` — put your changes aside and see if the crash goes away. If it
   does, the problem is your change.
3. If you didn't change anything, the data may be malformed for a specific
   stock. The error usually names it.

---

## Test problems

### 17 tests fail

**That's expected.** They were failing before you arrived. The known set:

- `test_casino_universe` — still assumes the original 8 themes / 55 stocks
- `test_casino_sector_aggregator`, `test_casino_sector_repository` — deal-log tests
- `test_casino_metadata_fetcher` — earnings BMO/AMC classification
- `test_congress_trades_fetcher` — congress fetch tests
- `test_casino_ui_loaders`, `test_tile_readability` — UI details that moved on

The number to watch is whether it *grows*. See
[`tests/README.md`](../../tests/README.md).

### Tests fail after my change

Run just the relevant file to see the detail:

```bash
./run test tests/test_casino_signals_computers.py -v
```

Read the `assert` line: it shows what was expected versus what happened.

### Tests hang or try to reach the internet

Unit tests must never make network calls. `./run test` already excludes the
integration ones. If a test still hangs, it's missing a mock — that's a bug in
the test.

---

## Git and data problems

### I accidentally changed the database

`data/snapshots.db` is production data. If `git status` shows it as modified and
you didn't mean to:

```bash
git checkout data/snapshots.db
```

That throws away your local change and restores the committed version. Do this
**before** committing anything.

If you already committed it but haven't pushed:

```bash
git reset --soft HEAD~1        # undo the commit, keep your other changes
git restore --staged data/snapshots.db
git checkout data/snapshots.db
```

If you already **pushed** it — stop and tell the repository owner. Don't try to
fix it with force-pushes.

### `git pull` conflicts on `data/snapshots.db`

This happens because the robot commits that file constantly. Take the remote
version — theirs is the real one:

```bash
git checkout --theirs data/snapshots.db
git add data/snapshots.db
```

Or just discard your local copy first and pull again:

```bash
git checkout data/snapshots.db
git pull
```

### I committed a secret / API key

Act quickly:

1. **Revoke the key** at whichever provider issued it. Assume it's compromised
   the moment it's pushed — removing it from git is not enough.
2. Issue a new one and put it in `.env` (local) or GitHub Secrets (production).
3. Tell the repository owner.

---

## Reddit problems

Reddit-related failures are their own world — Reddit closed its public API in
2026 and the project reads managed archives instead. Anything Reddit-shaped
(mention counts stuck, post pulls failing, "403", "Cloudflare") starts at
**[the Reddit runbook](../runbooks/reddit-local-runbook.md)**, not here.

---

## Still stuck?

1. Read the last line of the error, not the first.
2. `./run check`
3. `./run clean` then `./run setup` — clears caches and reinstalls. Safe; it
   won't touch your data or your `.env`.
4. Search the error text in the [docs index](../README.md).
5. Ask the repository owner, and include: what you ran, the last 10 lines of
   output, and what `./run check` says.

---

**Back to:** [the docs index](../README.md) · [the README](../../README.md)
