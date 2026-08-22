# `tests/` — the automated checks

~900 small checks that the logic still does what it's supposed to. They run in
about a minute and need no internet.

```bash
./run verify                                 # the full sweep — start here
./run test                                   # everything (offline)
./run test tests/test_casino_rsi.py -v       # one file, verbose
./run test -k "sector"                       # everything matching "sector"
```

---

## ⚠️ 17 failures are expected

They were failing before you arrived and are **not** a sign your setup is
broken. As of 2026-08-22:

| Test file | Why it fails |
|---|---|
| `test_casino_universe.py` (2) | Still asserts the original 8 themes / 55 stocks; there are now 12 and 64 |
| `test_casino_sector_repository.py` (4) | Deal-log storage tests |
| `test_casino_sector_aggregator.py` (2) | Deal-log totalling tests |
| `test_congress_trades_fetcher.py` (5) | Congress fetcher tests |
| `test_casino_metadata_fetcher.py` (2) | Earnings BMO/AMC classification |
| `test_casino_ui_loaders.py` (1) | Sector metadata shape changed |
| `test_tile_readability.py` (1) | Asserts a dark-mode CSS rule the component no longer emits |

**The number to watch is whether it grows.** Note the count before you start
working; if it's higher afterwards, your change broke something.

If you fix any of these, delete its row from this table.

## How the tests are organised

The layout mirrors the packages under `src/`:

| Pattern | Covers |
|---|---|
| `test_casino_*.py` | `src/casino_dashboard/` — the dashboard |
| `market/test_*.py` | `src/core/market/` — indicators and the Reality Score |
| `test_reddit_*`, `test_subreddit_*`, `test_social_media_*`, `test_apewisdom_*`, `test_arctic_shift*`, `test_apify_*` | `src/core/social_media/` |
| `test_storage_*`, `test_worker_pool_*`, `test_orchestration*`, `test_fintwit_*`, `test_rate_limiter*`, `test_reconciler*` | `src/fintwit/` |
| `test_youtube_client`, `test_transcripts`, `test_analyzer` | `src/ticker_digest/` |
| `test_migrate_*` | the migration scripts |

`conftest.py` holds fixtures shared by everything.

## Two rules

**1. No network calls in unit tests.** Every external service is mocked. A test
that reaches the internet is slow, flaky, and fails on a plane — that's a bug
in the test, not bad luck.

**2. Tests that genuinely need the internet are marked.** They carry
`@pytest.mark.integration` and are excluded by default:

```bash
./run test                                # skips them (this is the default)
.venv/bin/python -m pytest -m integration  # runs only them, and does hit the network
```

## Writing a test

Follow the file next door — the existing style is consistent. In short:

```python
def test_return_is_none_without_enough_history():
    result = compute_return(history=[], days=30)
    assert result is None
```

- Name it after the behaviour, not the function.
- One behaviour per test.
- Use `mocker` (from `pytest-mock`) to stand in for anything external.
- Cover the boring edges: empty input, one item, missing value. That's where
  the real bugs live.

The easiest things to test are `src/casino_dashboard/signals/` and
`src/casino_dashboard/db/` — pure logic, no I/O.

## The three regression suites

Beyond the unit tests, three files exist specifically to catch "it still works,
but not the same way":

| File | Catches |
|---|---|
| `test_public_api.py` | A name stopped resolving from where callers import it, or an entry point changed shape |
| `test_pages_render.py` | A page raises on load — the gap unit tests structurally cannot see |
| `test_production_parity.py` | The schema drifted from production, or the same inputs now produce different numbers |

The parity checks are marked `parity` and excluded from `./run test` because
they take ~20s. `./run verify` runs everything. Full explanation in
[Verifying a change](../docs/runbooks/verifying-a-change.md).

## What isn't tested

**How a page looks.** `test_pages_render.py` proves a screen doesn't crash. It
says nothing about layout, colour or ordering.

That's why the project's rule is: **open the page in a browser before merging a
UI change.** Green tests are not evidence that a screen looks right.
