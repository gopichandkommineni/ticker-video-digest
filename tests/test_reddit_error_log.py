"""Tests for the Reddit pipeline's error log (why outside calls failed)."""
import json

import pytest

from core.social_media.reddit import error_log


@pytest.fixture(autouse=True)
def _clean():
    error_log.clear()
    yield
    error_log.clear()


def test_record_keeps_reason_and_context_and_drops_empty_values():
    rec = error_log.record("arctic_shift", 422, "  Timeout  ", subreddit="stocks", query=None, x="")
    assert rec.reason == "Timeout" and rec.context == {"subreddit": "stocks"}
    assert error_log.recent("arctic_shift") == [rec] and error_log.recent("digest_llm") == []


def test_summary_groups_repeats_with_a_count_and_an_example():
    for q in ("RKLB", "Rocket Lab", "RKLB"):
        error_log.record("arctic_shift", 422, "Timeout", subreddit="stocks", query=q)
    error_log.record("arctic_shift", 0, "connection reset", subreddit="options")
    lines = error_log.summary_lines("arctic_shift")
    assert lines[0] == "### Why calls failed (4)"
    assert "| arctic_shift | 422 | Timeout | 3 | subreddit=stocks, query=RKLB |" in lines
    assert "| arctic_shift | — | connection reset | 1 | subreddit=options |" in lines
    assert error_log.summary_lines("digest_llm") == []


def test_log_file_gets_one_json_line_per_failure(tmp_path, monkeypatch):
    path = tmp_path / "logs" / "errors.jsonl"
    monkeypatch.setenv("REDDIT_ERROR_LOG", str(path))
    error_log.record("digest_llm", 0, "Claude plan usage limit reached", ticker="RKLB")
    error_log.record("arctic_shift", 422, "Timeout", subreddit="stocks")
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert [r["source"] for r in rows] == ["digest_llm", "arctic_shift"]
    back = error_log.read_log(path, limit=1)
    assert len(back) == 1 and back[0].reason == "Timeout"
    assert error_log.read_log(tmp_path / "missing.jsonl") == []


def test_an_unwritable_log_never_breaks_the_run(tmp_path, monkeypatch):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    monkeypatch.setenv("REDDIT_ERROR_LOG", str(blocker / "errors.jsonl"))
    assert error_log.record("arctic_shift", 500, "boom").reason == "boom"


def test_ingest_report_shows_the_reasons():
    from casino_dashboard.jobs.reddit_ingest import render
    from core.social_media.reddit.ingest import IngestReport
    from datetime import datetime, timezone
    error_log.record("arctic_shift", 422, "Timeout", subreddit="stocks", query="RKLB")
    rep = IngestReport(run_id=1, status="partial", window_start=datetime.now(tz=timezone.utc),
                       days_back=7, tickers=1)
    out = "\n".join(render(rep, set()))
    assert "### Why calls failed (1)" in out and "| arctic_shift | 422 | Timeout | 1 |" in out


def test_digest_failures_are_recorded(tmp_path):
    from core.social_media.reddit.digest import DigestConfig, GeminiError, run_digest
    from core.social_media.reddit.ingest import db
    from datetime import datetime, timedelta, timezone
    now = datetime.now(tz=timezone.utc)
    path = tmp_path / "r.db"
    conn = db.connect(path)
    db.upsert_post(conn, post_id="p1", subreddit="RKLB", author="u", title="t", body="b",
                   url="https://reddit.com/r/RKLB/comments/p1/", created_at=now - timedelta(hours=2),
                   score=5, num_comments=1, now=now - timedelta(hours=1))
    db.link_ticker(conn, "p1", "RKLB", "subreddit", "RKLB")
    conn.commit()
    conn.close()

    class Broken:
        model, call_delay = "fake", 0.0

        def generate_json(self, *a):
            raise GeminiError("HTTP 500: backend error")

    run_digest(["RKLB"], Broken(), db_path=path, cfg=DigestConfig(call_delay=0), now=now)
    rec = error_log.recent("digest_llm")[0]
    assert rec.reason == "HTTP 500: backend error"
    assert rec.context == {"ticker": "RKLB", "model": "fake", "effect": "stock skipped"}
