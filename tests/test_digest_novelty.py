"""Novelty detection — the deterministic half is exact, the LLM half is mocked."""
from datetime import datetime, timezone

import pytest

from core.models import Citation, Claim
from ticker_digest.novelty import (
    assess,
    claims_from_insights,
    classify_novelty,
    fingerprint,
    partition,
    rank_claims,
    similarity,
    tokenise,
)

from .digest_helpers import make_insights, tool_response


def _known(text: str, kind: str = "catalyst") -> Claim:
    return Claim(
        ticker="RKLB",
        kind=kind,
        text=text,
        citations=[
            Citation(video_id="old01", timestamp_seconds=5, quote_paraphrase=text)
        ],
        fingerprint=fingerprint(kind, text),
        novelty="new",
        first_seen_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
    )


# ---------------------------------------------------------------------------
# Text normalisation
# ---------------------------------------------------------------------------


def test_tokenise_drops_stopwords_and_case() -> None:
    assert tokenise("The company will WIN a contract") == {"win", "contract"}


def test_fingerprint_is_stable_under_word_order_and_punctuation() -> None:
    a = fingerprint("catalyst", "Neutron launch slipped to Q4")
    b = fingerprint("catalyst", "neutron launch, slipped to q4!")
    assert a == b


def test_fingerprint_separates_kinds() -> None:
    text = "Launch delayed to Q4"
    assert fingerprint("catalyst", text) != fingerprint("red_flag", text)


@pytest.mark.parametrize(
    "a, b, expected",
    [
        ("contract win", "contract win", 1.0),
        ("contract win", "totally different words here", 0.0),
    ],
)
def test_similarity_endpoints(a: str, b: str, expected: float) -> None:
    assert similarity(tokenise(a), tokenise(b)) == expected


def test_similarity_of_empty_sets_is_zero() -> None:
    assert similarity(set(), tokenise("anything")) == 0.0


# ---------------------------------------------------------------------------
# Flattening extractions into claims
# ---------------------------------------------------------------------------


def test_claims_from_insights_covers_all_three_kinds() -> None:
    insights = [
        make_insights(
            "vid001",
            catalysts=["New defence contract"],
            red_flags=["Cash burn accelerating"],
            upcoming_events=["Earnings call on May 8"],
        )
    ]

    claims = claims_from_insights("rklb", insights)

    assert [c.kind for c in claims] == ["catalyst", "red_flag", "upcoming_event"]
    assert all(c.ticker == "RKLB" for c in claims)
    assert claims[0].citations[0].timestamp_seconds == 10


def test_duplicates_within_the_batch_merge_into_one_claim_with_both_citations() -> None:
    insights = [
        make_insights("vid001", catalysts=["New defence contract"]),
        make_insights("vid002", catalysts=["new defence contract"]),
    ]

    claims = claims_from_insights("RKLB", insights)

    assert len(claims) == 1
    assert claims[0].source_count == 2
    assert [c.video_id for c in claims[0].citations] == ["vid001", "vid002"]
    # Wording comes from the first (highest-ranked) source.
    assert claims[0].text == "New defence contract"


def test_source_count_counts_videos_not_citations() -> None:
    """One commentator repeating themselves is still one source."""
    insights = [
        make_insights("vid001", catalysts=["New defence contract"]),
        make_insights("vid001", catalysts=["New defence contract"]),
    ]

    claims = claims_from_insights("RKLB", insights)

    assert claims[0].source_count == 1


def test_claims_from_insights_ignores_blank_paraphrases() -> None:
    insights = [make_insights("vid001", catalysts=["   "])]
    assert claims_from_insights("RKLB", insights) == []


# ---------------------------------------------------------------------------
# Deterministic partition
# ---------------------------------------------------------------------------


def test_exact_repeat_is_marked_known_without_the_model() -> None:
    known = [_known("Neutron first launch scheduled for Q4")]
    claims = claims_from_insights(
        "RKLB", [make_insights("vid001", catalysts=["Neutron first launch scheduled for Q4"])]
    )

    restatements, candidates = partition(claims, known)

    assert candidates == []
    assert restatements[0].novelty == "known"
    assert restatements[0].related_claim == "Neutron first launch scheduled for Q4"


def test_near_duplicate_is_marked_known_with_the_similarity_score() -> None:
    known = [_known("Neutron rocket first launch scheduled for Q4 2026")]
    claims = claims_from_insights(
        "RKLB",
        [
            make_insights(
                "vid001",
                catalysts=["Neutron rocket first launch scheduled for late Q4 2026"],
            )
        ],
    )

    restatements, candidates = partition(claims, known)

    assert candidates == []
    assert "Near-duplicate" in restatements[0].novelty_reasoning


def test_unrelated_claim_survives_to_become_a_candidate() -> None:
    known = [_known("Neutron first launch scheduled for Q4")]
    claims = claims_from_insights(
        "RKLB", [make_insights("vid001", catalysts=["Signed a lease on a new Virginia factory"])]
    )

    restatements, candidates = partition(claims, known)

    assert restatements == []
    assert len(candidates) == 1


# ---------------------------------------------------------------------------
# LLM classification
# ---------------------------------------------------------------------------


def test_no_history_means_everything_is_new_and_no_call_is_made(mocker) -> None:
    anthropic_cls = mocker.patch("ticker_digest.novelty.anthropic.Anthropic")
    claims = claims_from_insights("RKLB", [make_insights("vid001", catalysts=["Anything"])])

    result = classify_novelty("RKLB", "Rocket Lab", claims, known=[])

    assert [c.novelty for c in result] == ["new"]
    anthropic_cls.assert_not_called()


def test_no_candidates_means_no_call_is_made(mocker) -> None:
    anthropic_cls = mocker.patch("ticker_digest.novelty.anthropic.Anthropic")

    assert classify_novelty("RKLB", "Rocket Lab", [], known=[_known("x")]) == []
    anthropic_cls.assert_not_called()


def test_classification_is_applied_by_index(mocker) -> None:
    payload = {
        "classifications": [
            {
                "index": 0,
                "novelty": "developing",
                "reasoning": "Adds a firm date to a tracked launch.",
                "related_claim": "Neutron first launch scheduled for Q4",
            },
            {
                "index": 1,
                "novelty": "new",
                "reasoning": "Nothing on record mentions a Virginia factory.",
                "related_claim": None,
            },
        ]
    }
    client = mocker.MagicMock()
    client.messages.create.return_value = tool_response("classify_claims", payload)
    mocker.patch("ticker_digest.novelty.anthropic.Anthropic", return_value=client)

    claims = claims_from_insights(
        "RKLB",
        [
            make_insights(
                "vid001",
                catalysts=["Neutron launch now firmly November 12", "Signed a Virginia factory lease"],
            )
        ],
    )
    known = [_known("Neutron first launch scheduled for Q4")]

    result = classify_novelty("RKLB", "Rocket Lab", claims, known)

    assert [c.novelty for c in result] == ["developing", "new"]
    assert result[0].related_claim == "Neutron first launch scheduled for Q4"
    assert result[1].related_claim is None


def test_unclassified_claims_default_to_new(mocker) -> None:
    """Under-reporting news is the worse failure, so an omission stays 'new'."""
    client = mocker.MagicMock()
    client.messages.create.return_value = tool_response(
        "classify_claims", {"classifications": []}
    )
    mocker.patch("ticker_digest.novelty.anthropic.Anthropic", return_value=client)

    claims = claims_from_insights("RKLB", [make_insights("vid001", catalysts=["Something"])])

    result = classify_novelty("RKLB", "Rocket Lab", claims, [_known("Unrelated tracked claim")])

    assert result[0].novelty == "new"


# ---------------------------------------------------------------------------
# assess() — both halves together
# ---------------------------------------------------------------------------


def test_assess_preserves_order_and_only_judges_the_survivors(mocker) -> None:
    client = mocker.MagicMock()
    client.messages.create.return_value = tool_response(
        "classify_claims",
        {
            "classifications": [
                {"index": 0, "novelty": "new", "reasoning": "Genuinely new.", "related_claim": None}
            ]
        },
    )
    mocker.patch("ticker_digest.novelty.anthropic.Anthropic", return_value=client)

    known = [_known("Neutron first launch scheduled for Q4")]
    claims = claims_from_insights(
        "RKLB",
        [
            make_insights(
                "vid001",
                catalysts=["Neutron first launch scheduled for Q4"],
                red_flags=["Signed a Virginia factory lease that stretches the balance sheet"],
            )
        ],
    )

    result = assess("RKLB", "Rocket Lab", claims, known)

    assert [c.fingerprint for c in result] == [c.fingerprint for c in claims]
    assert result[0].novelty == "known"
    assert result[1].novelty == "new"
    # Only the one unmatched claim was sent to the model.
    sent = client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "Virginia" in sent
    assert "0. [red_flag]" in sent


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------


def _ranked(novelty: str, *, sources: int = 1, corroborated: bool = False) -> Claim:
    return Claim(
        ticker="RKLB",
        kind="catalyst",
        text=f"{novelty}-{sources}-{corroborated}",
        citations=[
            Citation(
                video_id=f"vid{index}",
                timestamp_seconds=index,
                quote_paraphrase="x",
            )
            for index in range(sources)
        ],
        fingerprint=f"fp-{novelty}-{sources}-{corroborated}",
        novelty=novelty,
        newly_corroborated=corroborated,
    )


def test_rank_puts_new_first_then_developing_then_corroborated_then_known() -> None:
    claims = [
        _ranked("known"),
        _ranked("known", corroborated=True),
        _ranked("developing"),
        _ranked("new"),
    ]

    order = [c.novelty for c in rank_claims(claims)]

    assert order == ["new", "developing", "known", "known"]
    assert rank_claims(claims)[2].newly_corroborated is True


def test_within_a_band_more_sources_wins() -> None:
    lonely = _ranked("new", sources=1)
    crowded = _ranked("new", sources=4)

    assert rank_claims([lonely, crowded])[0] is crowded


def test_ranking_does_not_mutate_the_input() -> None:
    claims = [_ranked("known"), _ranked("new")]

    rank_claims(claims)

    assert [c.novelty for c in claims] == ["known", "new"]
