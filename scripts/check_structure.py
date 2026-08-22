"""Structure guard — keeps files and functions small enough to actually read.

Run it:

    ./run lint

The rules are in CONTRIBUTING.md. In short: a file over 400 lines or a
function over 60 lines is one nobody reads carefully, so this script fails
the build when the repo gets worse and tells you when it has got better.

It is a *ratchet*, not a cliff. Today's oversized files are listed in
BASELINE below with their current size. They are allowed to exist and allowed
to shrink; they are not allowed to grow, and no new one may appear.

Exit codes: 0 = fine (notes are not failures), 1 = the repo got worse.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
THIS_FILE = "scripts/check_structure.py"

# --- the budget ------------------------------------------------------------

FILE_MAX_LINES = 400
FUNCTION_MAX_LINES = 60

# Trees the guard reads. Tests and research probes are deliberately exempt:
# a long test file is repetitive rather than complex, and probes are
# throwaway experiments kept as a record.
CHECKED_PATHS = ["src", "pages", "scripts", "app.py"]

# Files already over budget when the guard was introduced (2026-08-22).
# Each may SHRINK or be removed. None may grow. Adding a row is not a fix —
# split the file instead.
BASELINE: dict[str, int] = {
    "src/core/social_media/reddit/subreddit_catalog.py": 594,
    "src/casino_dashboard/jobs/subreddit_catalog_run.py": 584,
    "src/casino_dashboard/jobs/daily_refresh.py": 551,
    "src/fintwit/storage/day_log.py": 501,
    "scripts/run_variance.py": 488,
    "src/core/social_media/reddit/subreddit_match.py": 474,
    "pages/02_Ticker_Detail.py": 471,
    "src/fintwit/orchestration/worker_pool.py": 425,
    "src/casino_dashboard/ui/components/tile.py": 421,
    "src/core/social_media/reddit/subreddit_discovery.py": 420,
}

# How many over-long functions the repo currently has. This number may go
# down. It may never go up.
FUNCTION_BUDGET = 45

# Every package directly under src/ must explain itself to a newcomer.
PACKAGE_README_ROOT = "src"


def _python_files() -> list[Path]:
    files: list[Path] = []
    for entry in CHECKED_PATHS:
        path = REPO_ROOT / entry
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(path.rglob("*.py")))
    return files


def _rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _long_functions(path: Path, source: str) -> list[tuple[str, int]]:
    """Every function in `source` longer than the budget, as (label, lines)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    found = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            length = (node.end_lineno or node.lineno) - node.lineno + 1
            if length > FUNCTION_MAX_LINES:
                found.append((f"{_rel(path)}::{node.name}", length))
    return found


def check_file_sizes(files: list[Path]) -> tuple[list[str], list[str]]:
    """No new oversized file; no baseline file may grow."""
    failures, notes = [], []
    seen: set[str] = set()

    for path in files:
        rel = _rel(path)
        lines = len(path.read_text(encoding="utf-8").splitlines())

        if rel not in BASELINE:
            if lines > FILE_MAX_LINES:
                failures.append(
                    f"{rel} is {lines} lines, over the {FILE_MAX_LINES}-line budget. "
                    f"Split it into modules with one job each — see CONTRIBUTING.md."
                )
            continue

        seen.add(rel)
        allowed = BASELINE[rel]
        if lines > allowed:
            failures.append(
                f"{rel} grew to {lines} lines (was {allowed}). Files on the baseline "
                f"may shrink, never grow — split it instead."
            )
        elif lines <= FILE_MAX_LINES:
            notes.append(
                f"{rel} is down to {lines} lines, under budget. "
                f"Delete its row from BASELINE in {THIS_FILE}."
            )
        elif lines < allowed:
            notes.append(f"{rel} shrank to {lines} lines — update its BASELINE row to {lines}.")

    for stale in sorted(set(BASELINE) - seen):
        notes.append(f"{stale} no longer exists — delete its row from BASELINE.")
    return failures, notes


def check_function_lengths(found: list[tuple[str, int]]) -> tuple[list[str], list[str]]:
    """A ratchet on how many over-long functions exist. It may only go down."""
    count = len(found)
    if count > FUNCTION_BUDGET:
        worst = sorted(found, key=lambda item: -item[1])[:5]
        detail = ", ".join(f"{name} ({length} lines)" for name, length in worst)
        return [
            f"{count} functions are over {FUNCTION_MAX_LINES} lines; the budget is "
            f"{FUNCTION_BUDGET}. Longest: {detail}."
        ], []
    if count < FUNCTION_BUDGET:
        return [], [
            f"only {count} functions are over {FUNCTION_MAX_LINES} lines (budget "
            f"{FUNCTION_BUDGET}). Lower FUNCTION_BUDGET in {THIS_FILE} to {count} "
            f"to lock the win in."
        ]
    return [], []


def check_package_readmes() -> list[str]:
    """Every package under src/ explains itself in one screen."""
    failures = []
    for package in sorted((REPO_ROOT / PACKAGE_README_ROOT).iterdir()):
        if not package.is_dir() or not (package / "__init__.py").exists():
            continue
        if not (package / "README.md").exists():
            failures.append(
                f"{_rel(package)}/ has no README.md. Every package explains itself "
                f"in one screen — see CONTRIBUTING.md."
            )
    return failures


def main() -> int:
    files = _python_files()
    found: list[tuple[str, int]] = []
    for path in files:
        found.extend(_long_functions(path, path.read_text(encoding="utf-8")))

    size_failures, size_notes = check_file_sizes(files)
    func_failures, func_notes = check_function_lengths(found)
    failures = size_failures + func_failures + check_package_readmes()

    for note in size_notes + func_notes:
        print(f"note: {note}")

    if failures:
        print()
        for failure in failures:
            print(f"FAIL: {failure}")
        print(f"\n{len(failures)} structure problem(s). See CONTRIBUTING.md.")
        return 1

    print(
        f"\nOK — {len(files)} files within budget "
        f"({len(found)} long functions, budget {FUNCTION_BUDGET})."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
