"""Portability checks for the shell scripts a person runs on their own computer.

macOS ships bash 3.2, which (in a UTF-8 locale) reads a non-ASCII character
right after `$NAME` as part of the variable name: "on $REF…" became the unset
variable `REF…` and, under `set -u`, stopped the run. Braces avoid it:
"on ${REF}…".
"""
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = [ROOT / "run", *sorted((ROOT / "scripts").glob("*.sh"))]
_BARE_VAR_THEN_NON_ASCII = re.compile(rb"\$[A-Za-z_][A-Za-z_0-9]*[\x80-\xff]")


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_no_bare_variable_before_non_ascii(script: Path) -> None:
    bad = [f"{script.name}:{n}: {line.decode(errors='replace').strip()}"
           for n, line in enumerate(script.read_bytes().splitlines(), 1)
           if _BARE_VAR_THEN_NON_ASCII.search(line)]
    assert not bad, "write ${NAME} before a non-ASCII character:\n" + "\n".join(bad)


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_parses(script: Path) -> None:
    subprocess.run(["bash", "-n", str(script)], check=True)
