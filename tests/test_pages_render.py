"""Every dashboard page renders without raising.

This is the gap the rest of the suite leaves open: ~900 tests cover the helpers
the pages call, and none of them opens a page. A refactor can move a function,
keep every unit test green, and still leave a screen throwing on load.

Streamlit's own AppTest runs a page top to bottom in-process, with no browser
and no server, and collects anything it raised. It reads the committed
`data/snapshots.db`, so these are real pages against real data.

What this does NOT check: that a page looks *right*. Nothing automated does.
Open it in a browser before merging a UI change — see CONTRIBUTING.md.
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

PAGES = [
    "app.py",
    "pages/00_Sector_Heat.py",
    "pages/01_All_Tickers.py",
    "pages/02_Ticker_Detail.py",
    "pages/03_Market_Reality_Check.py",
    "pages/05_Congress.py",
    "pages/06_Add_Stocks.py",
]

# Streamlit's AppTest does not populate the page registry that st.page_link
# reads, so any page using it raises KeyError('url_pathname') under test while
# working perfectly in a browser. Ignore this one exception and nothing else —
# a genuine error still fails the test.
KNOWN_HARNESS_ERRORS = ("'url_pathname'",)


def _is_harness_limitation(error: BaseException) -> bool:
    return str(error) in KNOWN_HARNESS_ERRORS


@pytest.mark.parametrize("page", PAGES)
def test_page_renders_without_exception(page: str) -> None:
    from streamlit.testing.v1 import AppTest

    path = REPO_ROOT / page
    assert path.exists(), f"{page} is listed here but not in the repo"

    app = AppTest.from_file(str(path), default_timeout=180)
    app.query_params["ticker"] = "RKLB"  # Ticker Detail reads this
    app.run()

    real_errors = [e.value for e in app.exception if not _is_harness_limitation(e.value)]
    assert not real_errors, (
        f"{page} raised on load: "
        + "; ".join(f"{type(e).__name__}: {e}" for e in real_errors)
    )


def test_every_page_file_is_covered() -> None:
    """A new page must be added to PAGES above, not silently skipped."""
    on_disk = {"app.py"} | {
        f"pages/{p.name}" for p in (REPO_ROOT / "pages").glob("*.py")
    }
    assert on_disk == set(PAGES), (
        f"pages/ and PAGES disagree. Only here: {sorted(set(PAGES) - on_disk)}. "
        f"Only on disk: {sorted(on_disk - set(PAGES))}."
    )
