"""Run the test suite and check the failing set is exactly the expected one.

`./run test` shows you 17 failures every time. A command that always ends in
red teaches people to stop reading it. So `./run verify` uses this instead: it
compares the set of failing tests against tests/known_failures.txt and is green
only when they match exactly.

That makes both directions visible:

  * a test that starts failing  -> a regression, fails here
  * a test that starts passing  -> delete its line, fails here until you do

Same ratchet as scripts/check_structure.py: the list may only get shorter.

Exit codes: 0 = the failing set is as expected, 1 = it changed.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
KNOWN_FAILURES = REPO_ROOT / "tests" / "known_failures.txt"
PYTEST_ARGS = ["-q", "--tb=no", "-m", "not integration and not parity"]

FAILED_LINE = re.compile(r"^(?:FAILED|ERROR) (\S+?)(?: - .*)?$", re.MULTILINE)


def _expected() -> set[str]:
    if not KNOWN_FAILURES.exists():
        return set()
    return {
        line.strip()
        for line in KNOWN_FAILURES.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    }


def _run_pytest() -> tuple[set[str], str]:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", *PYTEST_ARGS],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    return set(FAILED_LINE.findall(output)), output


def main() -> int:
    actual, output = _run_pytest()
    expected = _expected()

    summary = next(
        (line for line in reversed(output.splitlines()) if " passed" in line or " failed" in line),
        "",
    )
    print(summary.strip())

    new = sorted(actual - expected)
    fixed = sorted(expected - actual)

    if not new and not fixed:
        print(f"OK — {len(actual)} known failures, no new ones.")
        return 0

    if new:
        print(f"\nFAIL: {len(new)} test(s) started failing:")
        for node in new:
            print(f"  {node}")
        print("\nRun it on its own to see why:")
        print(f"  ./run test {new[0].split('::')[0]} -v")

    if fixed:
        print(f"\nFAIL: {len(fixed)} known failure(s) now pass — delete their lines:")
        for node in fixed:
            print(f"  {node}")
        print(f"\nRemove them from {KNOWN_FAILURES.relative_to(REPO_ROOT)} "
              f"and from the table in tests/README.md.")

    return 1


if __name__ == "__main__":
    sys.exit(main())
