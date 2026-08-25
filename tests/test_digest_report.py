"""Markdown rendering of a stored run — no network, no model."""
from datetime import datetime, timezone

from core.models import (
    Citation,
    Claim,
    DigestRequest,
    DigestRun,
    InsightThread,
    ThreadPost,
)
from ticker_digest.quality import score_videos
from ticker_digest.report import main, thread_to_markdown

from .digest_helpers import NOW, make_metadata

GENERATED = datetime(2026, 8, 25, 9, 30, tzinfo=timezone.utc)


def _claim(text: str, novelty: str = "new", videos=("vid001",), corroborated=False) -> Claim:
    return Claim(
        ticker="RKLB",
        kind="catalyst",
        text=text,
        citations=[
            Citation(video_id=v, timestamp_seconds=42, quote_paraphrase=text) for v in videos
        ],
        fingerprint=f"fp-{text[:6]}",
        novelty=novelty,
        newly_corroborated=corroborated,
    )


def _thread() -> InsightThread:
    return InsightThread(
        thread_id="abc123def456",
        ticker="RKLB",
        company_name="Rocket Lab",
        source_kind="ticker_search",
        source_label="RKLB",
        generated_at=GENERATED,
        video_count=2,
        new_claim_count=1,
        overall_sentiment="bullish",
        headline="Rocket Lab: one new contract",
        posts=[
            ThreadPost(
                position=1,
                headline="New defence contract",
                body="Two commentators flagged the award.",
                novelty="new",
                citations=[
                    Citation(
                        video_id="vid001",
                        timestamp_seconds=42,
                        quote_paraphrase="Award confirmed",
                    )
                ],
            )
        ],
    )


def _run(thread=None, videos=("vid001",), claims=None, skipped=None) -> DigestRun:
    return DigestRun(
        run_id="run001",
        request=DigestRequest(ticker="RKLB", company_name="Rocket Lab", days=7),
        generated_at=GENERATED,
        videos=score_videos([make_metadata(v) for v in videos], now=NOW),
        thread=thread,
        claims=claims or [],
        skipped=skipped or {},
    )


def test_a_full_run_renders_headline_sources_claims_and_posts() -> None:
    md = thread_to_markdown(_run(_thread(), claims=[_claim("New defence contract")]))

    assert "## RKLB — Rocket Lab" in md
    assert "**Rocket Lab: one new contract**" in md
    assert "`thread abc123def456`" in md
    assert "| Score | Channel | Video | Views | Length |" in md
    assert "### Claims" in md
    assert "**1. `NEW` New defence contract**" in md
    assert "[Award confirmed](https://youtube.com/watch?v=vid001&t=42s)" in md
    assert "Not investment advice" in md


def test_corroboration_is_marked_and_explained() -> None:
    md = thread_to_markdown(
        _run(_thread(), claims=[_claim("Cash burn", "known", corroborated=True)])
    )

    assert "`KNOWN ✦`" in md
    assert "never said it before" in md


def test_no_corroboration_means_no_dangling_footnote() -> None:
    md = thread_to_markdown(_run(_thread(), claims=[_claim("New defence contract")]))
    assert "✦" not in md


def test_a_run_with_no_videos_explains_that_nothing_was_spent() -> None:
    md = thread_to_markdown(_run(videos=()))

    assert "No videos about **RKLB**" in md
    assert "no model calls were made" in md
    assert "### Sources" not in md


def test_a_run_with_videos_but_no_thread_still_shows_what_was_tried() -> None:
    md = thread_to_markdown(_run(None, skipped={"vid001": "no captions available"}))

    assert "### Sources" in md
    assert "no captions available" in md
    assert "### No thread" in md


def test_pipes_in_titles_do_not_break_the_table() -> None:
    run = _run(_thread(), claims=[_claim("Contract | award")])
    run.videos[0].metadata.title = "RKLB | the whole story"

    md = thread_to_markdown(run)

    assert "RKLB \\| the whole story" in md
    assert "Contract \\| award" in md


def test_cli_entry_reads_a_file(tmp_path, capsys) -> None:
    path = tmp_path / "run.json"
    path.write_text(_run(_thread()).model_dump_json())

    assert main([str(path)]) == 0
    assert "## RKLB — Rocket Lab" in capsys.readouterr().out


def test_cli_entry_reads_stdin(monkeypatch, capsys) -> None:
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO(_run(_thread()).model_dump_json()))

    assert main(["-"]) == 0
    assert "Rocket Lab: one new contract" in capsys.readouterr().out


def test_cli_entry_rejects_wrong_arguments(capsys) -> None:
    assert main([]) == 2
    assert "usage:" in capsys.readouterr().err
