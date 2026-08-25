"""CLI wiring for the digest commands — the pipeline and store are mocked."""
from datetime import datetime, timezone

import pytest

from core.models import (
    Citation,
    Claim,
    DigestRequest,
    DigestRun,
    InsightThread,
    ThreadPost,
)
from ticker_digest.cli import claim_summary, main, render_thread
from ticker_digest.quality import score_videos
from ticker_digest.sources import SourceResolutionError

from .digest_helpers import NOW, make_metadata


def _thread() -> InsightThread:
    return InsightThread(
        thread_id="th001",
        ticker="RKLB",
        company_name="Rocket Lab",
        source_kind="ticker_search",
        source_label="RKLB",
        generated_at=datetime(2026, 4, 20, 12, 0, tzinfo=timezone.utc),
        video_count=2,
        new_claim_count=1,
        overall_sentiment="bullish",
        headline="Rocket Lab: one genuinely new contract",
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


def _claim(novelty: str, videos: tuple[str, ...] = ("vid001",), corroborated=False) -> Claim:
    return Claim(
        ticker="RKLB",
        kind="catalyst",
        text=f"claim-{novelty}-{videos}",
        citations=[
            Citation(video_id=v, timestamp_seconds=1, quote_paraphrase="x")
            for v in videos
        ],
        fingerprint=f"fp-{novelty}-{videos}",
        novelty=novelty,
        newly_corroborated=corroborated,
    )


def _run(
    thread: InsightThread | None = None,
    videos=("vid001",),
    skipped=None,
    claims=None,
) -> DigestRun:
    return DigestRun(
        run_id="run001",
        request=DigestRequest(ticker="RKLB", company_name="Rocket Lab"),
        generated_at=NOW,
        videos=score_videos([make_metadata(v) for v in videos], now=NOW),
        thread=thread,
        skipped=skipped or {},
        claims=claims or [],
    )


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def test_render_thread_shows_novelty_citations_and_the_disclaimer() -> None:
    text = render_thread(_thread())

    assert "Rocket Lab: one genuinely new contract" in text
    assert "1. [NEW] New defence contract" in text
    assert "https://youtube.com/watch?v=vid001&t=42s" in text
    assert "Not investment advice." in text


# ---------------------------------------------------------------------------
# ticker subcommand
# ---------------------------------------------------------------------------


def test_ticker_command_prints_the_thread(mocker, capsys) -> None:
    mocker.patch("ticker_digest.sources.resolve_company_name", return_value="Rocket Lab")
    run_digest = mocker.patch(
        "ticker_digest.pipeline.run_digest", return_value=_run(_thread())
    )

    assert main(["ticker", "rklb"]) == 0

    out = capsys.readouterr().out
    assert "Sources (1 analysed)" in out
    assert "[NEW] New defence contract" in out
    request = run_digest.call_args.args[0]
    assert request.ticker == "RKLB"
    assert request.source_kind == "ticker_search"


def test_channel_flag_switches_the_source(mocker) -> None:
    mocker.patch("ticker_digest.sources.resolve_company_name", return_value="Rocket Lab")
    run_digest = mocker.patch(
        "ticker_digest.pipeline.run_digest", return_value=_run(_thread())
    )

    assert main(["ticker", "RKLB", "--channel", "@spaceinvesting", "--days", "30"]) == 0

    request = run_digest.call_args.args[0]
    assert request.source_kind == "channel"
    assert request.channel_query == "@spaceinvesting"
    assert request.days == 30


def test_company_flag_skips_the_lookup(mocker) -> None:
    lookup = mocker.patch("ticker_digest.sources.resolve_company_name")
    run_digest = mocker.patch(
        "ticker_digest.pipeline.run_digest", return_value=_run(_thread())
    )

    main(["ticker", "RKLB", "--company", "Rocket Lab USA"])

    lookup.assert_not_called()
    assert run_digest.call_args.args[0].company_name == "Rocket Lab USA"


def test_unresolvable_channel_exits_nonzero(mocker, capsys) -> None:
    mocker.patch("ticker_digest.sources.resolve_company_name", return_value="Rocket Lab")
    mocker.patch(
        "ticker_digest.pipeline.run_digest",
        side_effect=SourceResolutionError("No YouTube channel matched 'nope'"),
    )

    assert main(["ticker", "RKLB", "--channel", "nope"]) == 1
    assert "No YouTube channel matched" in capsys.readouterr().err


def test_no_videos_says_so_without_failing(mocker, capsys) -> None:
    mocker.patch("ticker_digest.sources.resolve_company_name", return_value="Rocket Lab")
    mocker.patch("ticker_digest.pipeline.run_digest", return_value=_run(videos=()))

    assert main(["ticker", "RKLB"]) == 0
    assert "No videos about RKLB" in capsys.readouterr().out


def test_transcript_failures_are_reported_when_there_is_no_thread(mocker, capsys) -> None:
    mocker.patch("ticker_digest.sources.resolve_company_name", return_value="Rocket Lab")
    mocker.patch(
        "ticker_digest.pipeline.run_digest",
        return_value=_run(None, skipped={"vid001": "no captions available"}),
    )

    assert main(["ticker", "RKLB"]) == 0
    out = capsys.readouterr().out
    assert "no thread" in out
    assert "no captions available" in out


def test_no_store_flag_is_passed_through(mocker) -> None:
    mocker.patch("ticker_digest.sources.resolve_company_name", return_value="Rocket Lab")
    run_digest = mocker.patch(
        "ticker_digest.pipeline.run_digest", return_value=_run(_thread())
    )

    main(["ticker", "RKLB", "--no-store"])

    assert run_digest.call_args.kwargs["persist"] is False


# ---------------------------------------------------------------------------
# threads subcommand
# ---------------------------------------------------------------------------


def test_threads_lists_stored_threads(mocker, capsys) -> None:
    mocker.patch("ticker_digest.store.list_threads", return_value=[_thread()])

    assert main(["threads", "--ticker", "RKLB"]) == 0
    out = capsys.readouterr().out
    assert "th001" in out
    assert "Rocket Lab: one genuinely new contract" in out


def test_threads_show_prints_one_thread(mocker, capsys) -> None:
    mocker.patch("ticker_digest.store.get_thread", return_value=_thread())

    assert main(["threads", "--show", "th001"]) == 0
    assert "[NEW] New defence contract" in capsys.readouterr().out


def test_threads_show_unknown_id_exits_nonzero(mocker, capsys) -> None:
    mocker.patch("ticker_digest.store.get_thread", return_value=None)

    assert main(["threads", "--show", "nope"]) == 1
    assert "No thread with id nope" in capsys.readouterr().err


def test_threads_empty_list_is_not_an_error(mocker, capsys) -> None:
    mocker.patch("ticker_digest.store.list_threads", return_value=[])

    assert main(["threads"]) == 0
    assert "No stored threads" in capsys.readouterr().out


def test_unknown_subcommand_is_rejected() -> None:
    with pytest.raises(SystemExit):
        main(["nonsense"])


# ---------------------------------------------------------------------------
# Claim summary line
# ---------------------------------------------------------------------------


def test_claim_summary_counts_each_verdict() -> None:
    run = _run(claims=[_claim("new"), _claim("new"), _claim("developing"), _claim("known")])

    assert claim_summary(run) == "Claims: 2 new · 1 developing · 1 known"


def test_claim_summary_calls_out_corroboration_and_multiple_sources() -> None:
    run = _run(
        claims=[
            _claim("known", ("vid001", "vid002"), corroborated=True),
            _claim("new"),
        ]
    )

    summary = claim_summary(run)

    assert "1 newly corroborated" in summary
    assert "1 backed by more than one video" in summary


def test_ticker_command_prints_the_claim_summary(mocker, capsys) -> None:
    mocker.patch("ticker_digest.sources.resolve_company_name", return_value="Rocket Lab")
    mocker.patch(
        "ticker_digest.pipeline.run_digest",
        return_value=_run(_thread(), claims=[_claim("new")]),
    )

    main(["ticker", "RKLB"])

    assert "Claims: 1 new" in capsys.readouterr().out


def test_the_sources_header_counts_skipped_videos_separately(mocker, capsys) -> None:
    mocker.patch("ticker_digest.sources.resolve_company_name", return_value="Rocket Lab")
    mocker.patch(
        "ticker_digest.pipeline.run_digest",
        return_value=_run(
            _thread(),
            videos=("vid001", "vid002", "vid003"),
            skipped={"vid002": "no captions available"},
        ),
    )

    main(["ticker", "RKLB"])

    assert "Sources (2 analysed, 1 skipped)" in capsys.readouterr().out
