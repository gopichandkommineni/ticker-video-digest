"""End-to-end pipeline — every external call (YouTube, captions, Claude) is mocked."""
from core.models import (
    ChannelInfo,
    Citation,
    Claim,
    DigestRequest,
    InsightThread,
    SourceSelection,
)
from ticker_digest import store
from ticker_digest.pipeline import mark_corroboration, run_digest
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
    mocker.patch(
        "ticker_digest.pipeline.select_videos",
        return_value=SourceSelection(videos=scored, channel=channel, considered=len(scored)),
    )

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
    mocker.patch(
        "ticker_digest.pipeline.select_videos", return_value=SourceSelection()
    )
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


# ---------------------------------------------------------------------------
# mark_corroboration — pure, no pipeline needed
# ---------------------------------------------------------------------------


def _claim(novelty: str = "known", videos: tuple[str, ...] = ("vid001",)) -> Claim:
    return Claim(
        ticker="RKLB",
        kind="catalyst",
        text="New defence contract",
        citations=[
            Citation(video_id=v, timestamp_seconds=10, quote_paraphrase="award")
            for v in videos
        ],
        fingerprint="fp1",
        novelty=novelty,
    )


def test_a_new_channel_repeating_an_old_claim_is_newly_corroborated() -> None:
    marked = mark_corroboration(
        [_claim("known", ("vid002",))],
        known_channels={"fp1": {"chan_A"}},
        channel_by_video={"vid002": "chan_B"},
    )

    assert marked[0].newly_corroborated is True


def test_the_same_channel_repeating_itself_is_not_corroboration() -> None:
    marked = mark_corroboration(
        [_claim("known", ("vid002",))],
        known_channels={"fp1": {"chan_A"}},
        channel_by_video={"vid002": "chan_A"},
    )

    assert marked[0].newly_corroborated is False


def test_a_new_claim_is_never_flagged_as_corroborated() -> None:
    marked = mark_corroboration(
        [_claim("new")],
        known_channels={},
        channel_by_video={"vid001": "chan_A"},
    )

    assert marked[0].newly_corroborated is False


def test_history_without_channel_attribution_stays_unflagged() -> None:
    """A pre-v2 database can't answer this, so we don't pretend it can."""
    from ticker_digest import store

    marked = mark_corroboration(
        [_claim("known", ("vid002",))],
        known_channels={"fp1": {store.UNKNOWN_CHANNEL}},
        channel_by_video={"vid002": "chan_B"},
    )

    assert marked[0].newly_corroborated is False


def test_pipeline_hands_the_thread_ranked_claims(mocker, tmp_path) -> None:
    mocks = _wire(mocker)
    # assess() is stubbed in _wire to pass claims through; make it label them
    # so ranking has something to sort on.
    labels = iter(["known", "new"])
    mocker.patch(
        "ticker_digest.pipeline.assess",
        side_effect=lambda t, c, claims, known: [
            claim.model_copy(update={"novelty": next(labels)}) for claim in claims
        ],
    )

    run = run_digest(_request(), db_path=tmp_path / "d.db")

    assert [c.novelty for c in run.claims] == ["new", "known"]
    assert mocks["build"].call_args.kwargs["claims"][0].novelty == "new"


# ---------------------------------------------------------------------------
# Backfilling past videos with no captions
# ---------------------------------------------------------------------------


def _pool(mocker, ids, *, with_captions, extraction_error_on=()):
    """Rank `ids`, give captions only to `with_captions`, wire the rest."""
    scored = score_videos([make_metadata(v) for v in ids], now=NOW)
    # score_videos sorts; keep the caller's order so "further down the list"
    # means what the test says it means.
    order = {v: i for i, v in enumerate(ids)}
    scored.sort(key=lambda sv: order[sv.metadata.video_id])
    mocker.patch(
        "ticker_digest.pipeline.select_videos",
        return_value=SourceSelection(videos=scored, considered=len(scored)),
    )

    mocker.patch(
        "ticker_digest.pipeline.get_transcript",
        side_effect=lambda vid: mocker.MagicMock() if vid in with_captions else None,
    )

    def _extract(transcript, metadata):
        if metadata.video_id in extraction_error_on:
            raise RuntimeError("model hiccup")
        return make_insights(metadata.video_id, catalysts=[f"from {metadata.video_id}"])

    mocker.patch("ticker_digest.pipeline.extract_insights", side_effect=_extract)
    mocker.patch("ticker_digest.pipeline.assess", side_effect=lambda t, c, claims, known: claims)
    thread = mocker.patch("ticker_digest.pipeline.build_thread")
    thread.return_value = None
    return thread


def test_a_video_without_captions_is_replaced_from_further_down(mocker, tmp_path) -> None:
    """The reported failure: 5 slots, 2 caption-less videos, only 3 analysed."""
    _pool(mocker, ["a", "b", "c", "d", "e"], with_captions={"a", "c", "e"})

    run = run_digest(
        _request(max_videos=3), db_path=tmp_path / "d.db", persist=False
    )

    assert [ins.video_id for ins in run.insights] == ["a", "c", "e"]
    assert set(run.skipped) == {"b", "d"}


def test_it_stops_as_soon_as_it_has_enough(mocker, tmp_path) -> None:
    """Ranked lower means unread, not analysed-anyway."""
    _pool(mocker, ["a", "b", "c", "d", "e"], with_captions=set("abcde"))

    run = run_digest(_request(max_videos=2), db_path=tmp_path / "d.db", persist=False)

    assert [ins.video_id for ins in run.insights] == ["a", "b"]
    # c, d and e were never even reached for.
    assert [sv.metadata.video_id for sv in run.videos] == ["a", "b"]


def test_it_gives_up_rather_than_walking_the_whole_list(mocker, tmp_path) -> None:
    """A ticker whose videos all lack captions must not walk 50 of them."""
    ids = [f"v{i}" for i in range(30)]
    _pool(mocker, ids, with_captions=set())

    run = run_digest(_request(max_videos=2), db_path=tmp_path / "d.db", persist=False)

    # max_videos x TRANSCRIPT_ATTEMPT_MULTIPLIER, and no further.
    assert len(run.videos) == 6
    assert run.insights == []
    assert run.thread is None


def test_a_paid_extraction_failure_is_not_backfilled(mocker, tmp_path) -> None:
    """Captions are free to check; an extraction is already paid for.

    Replacing a video that failed after the model call would spend twice to
    fill a quota, so the run reports one fewer instead.
    """
    _pool(mocker, ["a", "b", "c"], with_captions=set("abc"), extraction_error_on={"a"})

    run = run_digest(_request(max_videos=2), db_path=tmp_path / "d.db", persist=False)

    assert [ins.video_id for ins in run.insights] == ["b"]
    assert "extraction failed" in run.skipped["a"]
    assert [sv.metadata.video_id for sv in run.videos] == ["a", "b"]


def test_the_thread_only_sees_videos_that_were_actually_read(mocker, tmp_path) -> None:
    thread = _pool(mocker, ["a", "b", "c"], with_captions={"b", "c"})

    run_digest(_request(max_videos=2), db_path=tmp_path / "d.db", persist=False)

    analysed = thread.call_args.kwargs["videos"]
    assert [sv.metadata.video_id for sv in analysed] == ["b", "c"]


def test_a_run_never_makes_more_extraction_calls_than_it_was_asked_for(
    mocker, tmp_path
) -> None:
    """The one spend guarantee available until budget metering lands."""
    _pool(
        mocker,
        ["a", "b", "c", "d", "e", "f"],
        with_captions={"b", "d", "e", "f"},
        extraction_error_on={"b", "d"},
    )
    extract = mocker.patch(
        "ticker_digest.pipeline.extract_insights",
        side_effect=RuntimeError("model hiccup"),
    )

    run_digest(_request(max_videos=3), db_path=tmp_path / "d.db", persist=False)

    assert extract.call_count == 3
