"""Thread synthesis — the Anthropic client is mocked; the guards around it are not."""
from core.models import Citation, Claim
from ticker_digest.quality import score_videos
from ticker_digest.thread import build_thread

from .digest_helpers import NOW, make_insights, make_metadata, tool_response


def _claim(text: str, novelty: str = "new", video_id: str = "vid001") -> Claim:
    return Claim(
        ticker="RKLB",
        kind="catalyst",
        text=text,
        citation=Citation(video_id=video_id, timestamp_seconds=42, quote_paraphrase=text),
        fingerprint=f"fp-{text[:8]}",
        novelty=novelty,
    )


def _draft(posts: list[dict], headline: str = "Rocket Lab: one new contract") -> dict:
    return {
        "headline": headline,
        "overall_sentiment": "bullish",
        "posts": posts,
    }


def _post(
    headline: str = "New defence contract",
    novelty: str = "new",
    citations: list[dict] | None = None,
) -> dict:
    return {
        "headline": headline,
        "body": "Two commentators flagged the award.",
        "novelty": novelty,
        "citations": citations
        if citations is not None
        else [
            {
                "video_id": "vid001",
                "timestamp_seconds": 42,
                "quote_paraphrase": "Contract award confirmed",
            }
        ],
    }


def _build(mocker, draft: dict, *, claims=None, videos=None):
    client = mocker.MagicMock()
    client.messages.create.return_value = tool_response("report_thread", draft)
    mocker.patch("ticker_digest.thread.anthropic.Anthropic", return_value=client)

    scored = videos if videos is not None else score_videos([make_metadata("vid001")], now=NOW)
    thread = build_thread(
        ticker="rklb",
        company_name="Rocket Lab",
        claims=claims if claims is not None else [_claim("New defence contract")],
        insights=[make_insights("vid001")],
        videos=scored,
        source_kind="ticker_search",
        source_label="RKLB",
        generated_at=NOW,
    )
    return thread, client


def test_happy_path_builds_a_numbered_thread(mocker) -> None:
    thread, _ = _build(mocker, _draft([_post(), _post("Cash burn", "developing")]))

    assert thread.ticker == "RKLB"
    assert [p.position for p in thread.posts] == [1, 2]
    assert thread.posts[0].novelty == "new"
    assert thread.video_count == 1
    assert thread.disclaimer.endswith("Not investment advice.")


def test_new_claim_count_is_computed_here_not_by_the_model(mocker) -> None:
    claims = [
        _claim("New defence contract", "new"),
        _claim("Launch date confirmed", "developing"),
        _claim("They dominate small launch", "known"),
    ]
    thread, _ = _build(mocker, _draft([_post()]), claims=claims)

    assert thread.new_claim_count == 1


def test_citations_to_videos_this_run_never_read_are_dropped(mocker) -> None:
    invented = [
        {
            "video_id": "hallucinated",
            "timestamp_seconds": 12,
            "quote_paraphrase": "Never said",
        },
        {
            "video_id": "vid001",
            "timestamp_seconds": 42,
            "quote_paraphrase": "Contract award confirmed",
        },
    ]
    thread, _ = _build(mocker, _draft([_post(citations=invented)]))

    assert [c.video_id for c in thread.posts[0].citations] == ["vid001"]


def test_thread_is_capped_at_eight_posts(mocker) -> None:
    thread, _ = _build(mocker, _draft([_post(f"Post {i}") for i in range(12)]))

    assert len(thread.posts) == 8
    assert thread.posts[-1].position == 8


def test_thread_id_is_stable_for_the_same_run(mocker) -> None:
    first, _ = _build(mocker, _draft([_post()]))
    second, _ = _build(mocker, _draft([_post()]))

    assert first.thread_id == second.thread_id


def test_prompt_carries_the_novelty_verdicts(mocker) -> None:
    claims = [_claim("Launch date confirmed", "developing")]
    _, client = _build(mocker, _draft([_post()]), claims=claims)

    sent = client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "developing" in sent
    assert "0 of 1 claims are new" in sent


def test_a_run_with_nothing_new_still_produces_a_thread(mocker) -> None:
    thread, _ = _build(
        mocker,
        _draft([_post("Nothing new this week", "known")], headline="RKLB: no new information"),
        claims=[_claim("They dominate small launch", "known")],
    )

    assert thread.new_claim_count == 0
    assert thread.posts[0].novelty == "known"
