"""Quality filters and reliability scoring — pure functions, no mocks needed."""
import pytest

from core.config import MIN_SUBSCRIBER_COUNT, MIN_VIDEO_DURATION_SECONDS
from ticker_digest.quality import (
    is_all_caps_title,
    is_spam_title,
    passes_quality_filters,
    reliability_score,
    score_videos,
    spam_emoji_count,
)

from .digest_helpers import NOW, make_metadata

# ---------------------------------------------------------------------------
# Title spam detection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "title, expected",
    [
        ("RKLB STOCK IS ABOUT TO EXPLODE", True),
        ("RKLB stock is about to explode", False),
        ("Rocket Lab Q3 Earnings Breakdown", False),
        ("WHY I AM BUYING MORE", True),
        # The ticker itself is upper-case by definition and must not count.
        ("RKLB analysis after earnings", False),
        # Too few judgeable words to call it.
        ("RKLB NOW", False),
    ],
)
def test_is_all_caps_title(title: str, expected: bool) -> None:
    assert is_all_caps_title(title, "RKLB") is expected


def test_spam_emoji_count_counts_repeats() -> None:
    assert spam_emoji_count("RKLB 🚀🚀🚀 to the moon") == 3
    assert spam_emoji_count("Rocket Lab earnings") == 0


def test_one_emoji_is_tolerated_but_two_is_not() -> None:
    assert is_spam_title("Rocket Lab earnings 🚀", "RKLB") is False
    assert is_spam_title("Rocket Lab earnings 🚀🔥", "RKLB") is True


# ---------------------------------------------------------------------------
# Quality gate
# ---------------------------------------------------------------------------


def test_good_video_passes() -> None:
    ok, reason = passes_quality_filters(make_metadata(), "RKLB")
    assert ok is True
    assert reason == ""


def test_short_video_is_rejected_with_a_reason() -> None:
    ok, reason = passes_quality_filters(
        make_metadata(duration=MIN_VIDEO_DURATION_SECONDS - 1), "RKLB"
    )
    assert ok is False
    assert "too short" in reason


def test_small_channel_is_rejected_with_a_reason() -> None:
    ok, reason = passes_quality_filters(
        make_metadata(subscribers=MIN_SUBSCRIBER_COUNT - 1), "RKLB"
    )
    assert ok is False
    assert "channel too small" in reason


def test_bait_title_is_rejected() -> None:
    ok, reason = passes_quality_filters(
        make_metadata(title="RKLB IS GOING PARABOLIC RIGHT NOW"), "RKLB"
    )
    assert ok is False
    assert "engagement bait" in reason


# ---------------------------------------------------------------------------
# Reliability scoring
# ---------------------------------------------------------------------------


def test_score_is_bounded_and_components_are_reported() -> None:
    total, components = reliability_score(make_metadata(), now=NOW)
    assert 0.0 <= total <= 1.0
    assert set(components) == {
        "subscribers",
        "views",
        "engagement",
        "depth",
        "recency",
    }
    assert all(0.0 <= value <= 1.0 for value in components.values())


def test_bigger_channel_outranks_smaller_at_equal_engagement() -> None:
    # Views scale with subscribers so the engagement component is identical and
    # only reach differs.
    big, _ = reliability_score(
        make_metadata(subscribers=400_000, views=40_000), now=NOW
    )
    small, _ = reliability_score(
        make_metadata(subscribers=1_000, views=100), now=NOW
    )
    assert big > small


def test_an_overperforming_small_channel_can_outrank_a_quiet_big_one() -> None:
    """Deliberate: views-per-subscriber is a signal, not noise.

    A 2k-subscriber channel whose video got 30k views said something people
    passed around; a 400k-subscriber channel whose video got 3k views did not.
    """
    overperformer, _ = reliability_score(
        make_metadata(subscribers=2_000, views=30_000), now=NOW
    )
    quiet_giant, _ = reliability_score(
        make_metadata(subscribers=400_000, views=3_000), now=NOW
    )
    assert overperformer > quiet_giant


def test_fresher_video_outranks_stale_all_else_equal() -> None:
    fresh, _ = reliability_score(make_metadata(age_days=0.5), now=NOW)
    stale, _ = reliability_score(make_metadata(age_days=45), now=NOW)
    assert fresh > stale


def test_longer_video_outranks_a_three_minute_take() -> None:
    deep, _ = reliability_score(make_metadata(duration=1_800), now=NOW)
    shallow, _ = reliability_score(make_metadata(duration=180), now=NOW)
    assert deep > shallow


def test_score_videos_returns_most_reliable_first() -> None:
    weak = make_metadata("weak", subscribers=600, views=300, duration=180, age_days=20)
    strong = make_metadata("strong", subscribers=300_000, views=90_000, duration=1_500)
    middle = make_metadata("middle", subscribers=20_000, views=9_000, duration=700)

    ranked = score_videos([weak, strong, middle], now=NOW)

    assert [sv.metadata.video_id for sv in ranked] == ["strong", "middle", "weak"]
    assert ranked[0].reliability_score > ranked[-1].reliability_score
    assert ranked[0].score_components["depth"] == 1.0
