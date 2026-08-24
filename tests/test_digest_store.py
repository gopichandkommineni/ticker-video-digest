"""Digest storage — every test writes to a tmp_path database, never the real one."""
from datetime import datetime, timedelta, timezone

from core.models import Citation, Claim, DigestRequest, DigestRun, InsightThread, ThreadPost
from ticker_digest import store

# Stored claims are filtered by a lookback window measured from *now*, so
# these fixtures are anchored to the clock rather than a fixed date.
NOW = datetime.now(timezone.utc)


def _claim(text: str, *, kind: str = "catalyst", fingerprint: str = "fp1") -> Claim:
    return Claim(
        ticker="RKLB",
        kind=kind,
        text=text,
        citation=Citation(video_id="vid001", timestamp_seconds=10, quote_paraphrase=text),
        fingerprint=fingerprint,
        novelty="new",
        novelty_reasoning="First time seen.",
    )


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
) -> DigestRun:
    return DigestRun(
        run_id=run_id,
        request=DigestRequest(ticker="RKLB", company_name="Rocket Lab"),
        generated_at=generated_at,
        videos=[],
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
    assert known[0].citation.video_id == "vid001"


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
