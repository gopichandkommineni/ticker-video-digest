"""End-to-end pipeline — every external call (YouTube, captions, Claude) is mocked."""
from core.models import ChannelInfo, DigestRequest, InsightThread
from ticker_digest import store
from ticker_digest.pipeline import run_digest
from ticker_digest.quality import score_videos

from .digest_helpers import NOW, make_insights, make_metadata


def _request(**overrides) -> DigestRequest:
    base = {"ticker": "RKLB", "company_name": "Rocket Lab", "max_videos": 2}
    return DigestRequest(**{**base, **overrides})


def _wire(
    mocker,
    *,
    videos=("vid001", "vid002"),
    transcripts=None,
    extraction_error_on=(),
    channel=None,
):
    """Patch the pipeline's four external dependencies and return the mocks."""
    scored = score_videos([make_metadata(v) for v in videos], now=NOW)
    mocker.patch("ticker_digest.pipeline.select_videos", return_value=(scored, channel))

    if transcripts is None:
        transcripts = {v: mocker.MagicMock() for v in videos}
    mocker.patch(
        "ticker_digest.pipeline.get_transcript",
        side_effect=lambda video_id: transcripts.get(video_id),
    )

    def _extract(transcript, metadata):
        if metadata.video_id in extraction_error_on:
            raise RuntimeError("model unavailable")
        return make_insights(metadata.video_id, catalysts=[f"Claim from {metadata.video_id}"])

    extract = mocker.patch("ticker_digest.pipeline.extract_insights", side_effect=_extract)

    assess = mocker.patch(
        "ticker_digest.pipeline.assess", side_effect=lambda t, c, claims, known: claims
    )

    thread = InsightThread(
        thread_id="th001",
        ticker="RKLB",
        company_name="Rocket Lab",
        source_kind="channel" if channel else "ticker_search",
        source_label=channel.title if channel else "RKLB",
        generated_at=NOW,
        video_count=len(scored),
        new_claim_count=1,
        overall_sentiment="bullish",
        headline="Rocket Lab: one new claim",
        posts=[],
    )
    build = mocker.patch("ticker_digest.pipeline.build_thread", return_value=thread)
    return {"extract": extract, "assess": assess, "build": build, "scored": scored}


def test_happy_path_runs_every_stage_and_stores_the_result(mocker, tmp_path) -> None:
    db = tmp_path / "digests.db"
    save = mocker.spy(store, "save_run")
    mocks = _wire(mocker)

    run = run_digest(_request(), db_path=db)

    assert len(run.insights) == 2
    assert len(run.claims) == 2
    assert run.thread is not None
    assert run.skipped == {}
    assert mocks["extract"].call_count == 2
    assert save.call_count == 1


def test_videos_without_captions_are_skipped_with_a_reason(mocker, tmp_path) -> None:
    mocks = _wire(mocker, transcripts={"vid001": mocker.MagicMock()})  # vid002 → None

    run = run_digest(_request(), db_path=tmp_path / "d.db")

    assert run.skipped == {"vid002": "no captions available"}
    assert len(run.insights) == 1
    # The dropped video must not reach the thread's citation allow-list.
    analysed = mocks["build"].call_args.kwargs["videos"]
    assert [sv.metadata.video_id for sv in analysed] == ["vid001"]


def test_one_failed_extraction_does_not_kill_the_run(mocker, tmp_path) -> None:
    _wire(mocker, extraction_error_on=("vid001",))

    run = run_digest(_request(), db_path=tmp_path / "d.db")

    assert "extraction failed" in run.skipped["vid001"]
    assert len(run.insights) == 1
    assert run.thread is not None


def test_no_usable_videos_yields_a_run_with_no_thread(mocker, tmp_path) -> None:
    mocker.patch("ticker_digest.pipeline.select_videos", return_value=([], None))
    mocker.patch("ticker_digest.pipeline.get_transcript", return_value=None)
    build = mocker.patch("ticker_digest.pipeline.build_thread")

    run = run_digest(_request(), db_path=tmp_path / "d.db")

    assert run.videos == []
    assert run.thread is None
    build.assert_not_called()


def test_novelty_is_judged_against_claims_stored_by_earlier_runs(mocker, tmp_path) -> None:
    db = tmp_path / "digests.db"
    mocks = _wire(mocker)

    run_digest(_request(), db_path=db)
    first_known = mocks["assess"].call_args.args[3]
    assert first_known == []

    run_digest(_request(), db_path=db)
    second_known = mocks["assess"].call_args.args[3]
    assert {c.text for c in second_known} == {"Claim from vid001", "Claim from vid002"}


def test_persist_false_leaves_the_database_untouched(mocker, tmp_path) -> None:
    db = tmp_path / "digests.db"
    _wire(mocker)

    run_digest(_request(), db_path=db, persist=False)

    assert store.list_threads(db_path=db) == []


def test_channel_runs_are_labelled_with_the_channel(mocker, tmp_path) -> None:
    channel = ChannelInfo(channel_id="UC" + "a" * 22, title="Space Investing")
    mocks = _wire(mocker, channel=channel)

    run = run_digest(
        _request(source_kind="channel", channel_query="Space Investing"),
        db_path=tmp_path / "d.db",
    )

    assert run.channel is not None and run.channel.title == "Space Investing"
    assert mocks["build"].call_args.kwargs["source_label"] == "Space Investing"


def test_claims_are_stamped_with_this_run_time(mocker, tmp_path) -> None:
    _wire(mocker)

    run = run_digest(_request(), db_path=tmp_path / "d.db")

    assert all(c.first_seen_at == run.generated_at for c in run.claims)
