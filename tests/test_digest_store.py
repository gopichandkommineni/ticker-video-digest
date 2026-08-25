"""Digest storage — every test writes to a tmp_path database, never the real one."""
import sqlite3
from datetime import datetime, timedelta, timezone

from core.models import (
    Citation,
    Claim,
    DigestRequest,
    DigestRun,
    InsightThread,
    ScoredVideo,
    ThreadPost,
)
from ticker_digest import store

from .digest_helpers import make_metadata

# Stored claims are filtered by a lookback window measured from *now*, so
# these fixtures are anchored to the clock rather than a fixed date.
NOW = datetime.now(timezone.utc)


def _claim(
    text: str,
    *,
    kind: str = "catalyst",
    fingerprint: str = "fp1",
    videos: tuple[str, ...] = ("vid001",),
) -> Claim:
    return Claim(
        ticker="RKLB",
        kind=kind,
        text=text,
        citations=[
            Citation(video_id=video_id, timestamp_seconds=10, quote_paraphrase=text)
            for video_id in videos
        ],
        fingerprint=fingerprint,
        novelty="new",
        novelty_reasoning="First time seen.",
    )


def _scored(*videos: tuple[str, str]) -> list:
    """ScoredVideo stubs carrying just the video → channel mapping."""
    return [
        ScoredVideo(
            metadata=make_metadata(video_id, channel_id=channel_id),
            reliability_score=0.5,
        )
        for video_id, channel_id in videos
    ]


def _thread(thread_id: str = "th001", generated_at: datetime = NOW) -> InsightThread:
    return InsightThread(
        thread_id=thread_id,
        ticker="RKLB",
        company_name="Rocket Lab",
        source_kind="ticker_search",
        source_label="RKLB",
        generated_at=generated_at,
        video_count=2,
        new_claim_count=1,
        overall_sentiment="bullish",
        headline="Rocket Lab: one genuinely new contract this week",
        posts=[
            ThreadPost(
                position=1,
                headline="New defence contract",
                body="Two commentators flagged an award announced on Tuesday.",
                novelty="new",
                citations=[
                    Citation(
                        video_id="vid001",
                        timestamp_seconds=42,
                        quote_paraphrase="Contract award confirmed",
                    )
                ],
            )
        ],
    )


def _run(
    run_id: str = "run001",
    *,
    claims: list[Claim] | None = None,
    thread: InsightThread | None = None,
    generated_at: datetime = NOW,
    videos: list | None = None,
) -> DigestRun:
    return DigestRun(
        run_id=run_id,
        request=DigestRequest(ticker="RKLB", company_name="Rocket Lab"),
        generated_at=generated_at,
        videos=videos if videos is not None else [],
        insights=[],
        claims=claims or [],
        thread=thread,
    )


def test_init_db_is_idempotent(tmp_path) -> None:
    db = tmp_path / "digests.db"
    store.init_db(db)
    store.init_db(db)
    assert db.exists()


def test_save_run_round_trips(tmp_path) -> None:
    db = tmp_path / "digests.db"
    run = _run(claims=[_claim("New defence contract")], thread=_thread())

    store.save_run(run, db_path=db)

    loaded = store.get_run("run001", db_path=db)
    assert loaded is not None
    assert loaded.request.ticker == "RKLB"
    assert len(loaded.claims) == 1

    thread = store.get_thread("th001", db_path=db)
    assert thread is not None
    assert thread.posts[0].citations[0].url.endswith("&t=42s")


def test_known_claims_returns_stored_claims(tmp_path) -> None:
    db = tmp_path / "digests.db"
    store.save_run(_run(claims=[_claim("New defence contract")]), db_path=db)

    known = store.known_claims("RKLB", db_path=db)

    assert len(known) == 1
    assert known[0].text == "New defence contract"
    assert [c.video_id for c in known[0].citations] == ["vid001"]


def test_known_claims_is_scoped_to_the_ticker(tmp_path) -> None:
    db = tmp_path / "digests.db"
    store.save_run(_run(claims=[_claim("New defence contract")]), db_path=db)

    assert store.known_claims("ASTS", db_path=db) == []


def test_first_seen_at_survives_a_second_sighting(tmp_path) -> None:
    """The whole point of the claims table: a repeat must not reset the date."""
    db = tmp_path / "digests.db"
    first = NOW - timedelta(days=10)
    store.save_run(
        _run("run001", claims=[_claim("New defence contract")], generated_at=first),
        db_path=db,
    )
    store.save_run(
        _run("run002", claims=[_claim("New defence contract")], generated_at=NOW),
        db_path=db,
    )

    known = store.known_claims("RKLB", db_path=db)
    assert len(known) == 1
    assert known[0].first_seen_at == first


def test_known_claims_respects_the_lookback_window(tmp_path) -> None:
    db = tmp_path / "digests.db"
    long_ago = datetime.now(timezone.utc) - timedelta(days=200)
    store.save_run(
        _run(claims=[_claim("Ancient news")], generated_at=long_ago), db_path=db
    )

    assert store.known_claims("RKLB", lookback_days=90, db_path=db) == []
    assert len(store.known_claims("RKLB", lookback_days=365, db_path=db)) == 1


def test_list_threads_is_newest_first_and_filterable(tmp_path) -> None:
    db = tmp_path / "digests.db"
    older = _thread("th_old", generated_at=NOW - timedelta(days=3))
    newer = _thread("th_new", generated_at=NOW)
    store.save_run(_run("run001", thread=older), db_path=db)
    store.save_run(_run("run002", thread=newer), db_path=db)

    threads = store.list_threads(db_path=db)
    assert [t.thread_id for t in threads] == ["th_new", "th_old"]

    assert len(store.list_threads(ticker="RKLB", db_path=db)) == 2
    assert store.list_threads(ticker="ASTS", db_path=db) == []


def test_missing_ids_return_none(tmp_path) -> None:
    db = tmp_path / "digests.db"
    assert store.get_thread("nope", db_path=db) is None
    assert store.get_run("nope", db_path=db) is None


def test_saving_the_same_run_twice_updates_rather_than_duplicates(tmp_path) -> None:
    db = tmp_path / "digests.db"
    run = _run(thread=_thread())
    store.save_run(run, db_path=db)
    store.save_run(run, db_path=db)

    assert len(store.list_threads(db_path=db)) == 1


# ---------------------------------------------------------------------------
# Citations and corroboration
# ---------------------------------------------------------------------------


def test_every_citation_survives_the_round_trip(tmp_path) -> None:
    db = tmp_path / "digests.db"
    claim = _claim("New defence contract", videos=("vid001", "vid002", "vid003"))

    store.save_run(_run(claims=[claim]), db_path=db)

    known = store.known_claims("RKLB", db_path=db)
    assert known[0].source_count == 3
    assert {c.video_id for c in known[0].citations} == {"vid001", "vid002", "vid003"}


def test_citations_record_the_channel_that_published_each_video(tmp_path) -> None:
    db = tmp_path / "digests.db"
    run = _run(
        claims=[_claim("New defence contract", videos=("vid001", "vid002"))],
        videos=_scored(("vid001", "chan_A"), ("vid002", "chan_B")),
    )

    store.save_run(run, db_path=db)

    assert store.known_claim_channels("RKLB", db_path=db) == {
        "fp1": {"chan_A", "chan_B"}
    }


def test_a_video_the_run_never_ranked_records_an_unknown_channel(tmp_path) -> None:
    db = tmp_path / "digests.db"
    run = _run(claims=[_claim("New defence contract")], videos=[])

    store.save_run(run, db_path=db)

    assert store.known_claim_channels("RKLB", db_path=db) == {
        "fp1": {store.UNKNOWN_CHANNEL}
    }


def test_a_second_sighting_adds_citations_without_duplicating_them(tmp_path) -> None:
    db = tmp_path / "digests.db"
    store.save_run(
        _run("run001", claims=[_claim("New defence contract", videos=("vid001",))]),
        db_path=db,
    )
    store.save_run(
        _run(
            "run002",
            claims=[_claim("New defence contract", videos=("vid001", "vid002"))],
        ),
        db_path=db,
    )

    known = store.known_claims("RKLB", db_path=db)
    assert len(known) == 1
    assert known[0].source_count == 2


def test_last_seen_at_moves_while_first_seen_at_holds(tmp_path) -> None:
    db = tmp_path / "digests.db"
    first = NOW - timedelta(days=5)
    store.save_run(
        _run("run001", claims=[_claim("New defence contract")], generated_at=first),
        db_path=db,
    )
    store.save_run(
        _run("run002", claims=[_claim("New defence contract")], generated_at=NOW),
        db_path=db,
    )

    with sqlite3.connect(db) as conn:
        first_seen, last_seen = conn.execute(
            "SELECT first_seen_at, last_seen_at FROM claims"
        ).fetchone()

    assert datetime.fromisoformat(first_seen) == first
    assert datetime.fromisoformat(last_seen) == NOW


# ---------------------------------------------------------------------------
# Migration from the v1 shape
# ---------------------------------------------------------------------------

_V1_SCHEMA = """
CREATE TABLE claims (
    ticker            TEXT    NOT NULL,
    fingerprint       TEXT    NOT NULL,
    kind              TEXT    NOT NULL,
    text              TEXT    NOT NULL,
    video_id          TEXT    NOT NULL,
    timestamp_seconds INTEGER NOT NULL,
    quote_paraphrase  TEXT    NOT NULL,
    novelty           TEXT    NOT NULL,
    novelty_reasoning TEXT    NOT NULL DEFAULT '',
    related_claim     TEXT,
    run_id            TEXT    NOT NULL,
    first_seen_at     TEXT    NOT NULL,
    PRIMARY KEY (ticker, fingerprint)
);
"""


def _write_v1_database(db, first_seen: datetime) -> None:
    with sqlite3.connect(db) as conn:
        conn.executescript(_V1_SCHEMA)
        conn.execute(
            "INSERT INTO claims VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "RKLB",
                "fp1",
                "catalyst",
                "New defence contract",
                "vid001",
                42,
                "Award confirmed",
                "new",
                "First time seen.",
                None,
                "run001",
                first_seen.isoformat(),
            ),
        )
        conn.commit()


def test_a_v1_database_migrates_in_place(tmp_path) -> None:
    db = tmp_path / "digests.db"
    first = NOW - timedelta(days=30)
    _write_v1_database(db, first)

    store.init_db(db)

    known = store.known_claims("RKLB", db_path=db)
    assert len(known) == 1
    assert known[0].text == "New defence contract"
    # The date that makes novelty mean anything must survive the migration.
    assert known[0].first_seen_at == first
    assert known[0].citations[0].timestamp_seconds == 42

    with sqlite3.connect(db) as conn:
        version = conn.execute("SELECT version FROM schema_version").fetchone()[0]
    assert version == store.SCHEMA_VERSION


def test_migrated_citations_are_marked_unknown_channel(tmp_path) -> None:
    """v1 didn't record channels, and guessing would be worse than admitting it."""
    db = tmp_path / "digests.db"
    _write_v1_database(db, NOW)

    store.init_db(db)

    assert store.known_claim_channels("RKLB", db_path=db) == {
        "fp1": {store.UNKNOWN_CHANNEL}
    }


def test_migration_is_idempotent(tmp_path) -> None:
    db = tmp_path / "digests.db"
    _write_v1_database(db, NOW)

    store.init_db(db)
    store.init_db(db)

    assert len(store.known_claims("RKLB", db_path=db)) == 1
