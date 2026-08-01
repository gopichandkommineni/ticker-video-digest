"""PR C — run_daily.py exit-code policy.

After the worker-pool cutover, `incomplete` is the normal post-delta state
(lingering mismatches the pool re-tries on later days). The daily Action should
go red only on `failed`, not `incomplete`.

The script has no main() — it runs on import — so we execute it via runpy with
ingest_all and close_connection mocked (the latter so the live DB is never
touched), and inspect the SystemExit code.
"""

from __future__ import annotations

import runpy

import pytest

from fintwit.orchestration.runner import RunResult

SCRIPT = "scripts/run_daily.py"


def _result(handle: str, outcome: str) -> RunResult:
    reason = ""
    if outcome == "incomplete":
        reason = "1 mismatch + 0 failed day-slots remain"
    return RunResult(handle=handle, outcome=outcome, reason=reason, days_ok=3)


def _run(results: list[RunResult], monkeypatch, capsys) -> tuple[int, str]:
    monkeypatch.setattr("fintwit.orchestration.runner.ingest_all", lambda *a, **k: results)
    # Never checkpoint/touch the live data/fintwit.db from a test.
    monkeypatch.setattr("fintwit.storage.close_connection", lambda *a, **k: None)
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", "/dev/null")
    code: int = 0
    try:
        runpy.run_path(SCRIPT, run_name="__main__")
    except SystemExit as e:
        code = 0 if e.code is None else (e.code if isinstance(e.code, int) else 1)
    out = capsys.readouterr().out
    return code, out


def _mix(ok=0, incomplete=0, failed=0) -> list[RunResult]:
    rs = []
    rs += [_result(f"ok{i}", "ok") for i in range(ok)]
    rs += [_result(f"inc{i}", "incomplete") for i in range(incomplete)]
    rs += [_result(f"fail{i}", "failed") for i in range(failed)]
    return rs


def test_exit_code_zero_when_all_ok(monkeypatch, capsys):
    code, _ = _run(_mix(ok=7), monkeypatch, capsys)
    assert code == 0


def test_exit_code_zero_when_incomplete_no_failed(monkeypatch, capsys):
    # The cutover scenario: 7 ok, 2 incomplete, 0 failed → green.
    code, _ = _run(_mix(ok=7, incomplete=2), monkeypatch, capsys)
    assert code == 0


def test_exit_code_one_when_any_failed(monkeypatch, capsys):
    code, _ = _run(_mix(ok=7, failed=1), monkeypatch, capsys)
    assert code == 1


def test_exit_code_one_when_failed_with_incomplete(monkeypatch, capsys):
    code, _ = _run(_mix(ok=5, incomplete=2, failed=2), monkeypatch, capsys)
    assert code == 1


def test_summary_printout_unchanged(monkeypatch, capsys):
    # Incomplete handles are still surfaced in the human-readable summary, with
    # the 'will retry tomorrow' note and the ✓/~/✗ markers — only the exit code
    # policy changed.
    results = [_result("good", "ok"), _result("aleabitoreddit", "incomplete")]
    code, out = _run(results, monkeypatch, capsys)
    assert code == 0
    assert "── FinTwit ingest summary ──" in out
    assert "✓ good: ok" in out
    assert "~ aleabitoreddit: incomplete" in out
    assert "will retry tomorrow" in out
    assert "ok=1 failed=0 incomplete=1 skipped=0" in out
