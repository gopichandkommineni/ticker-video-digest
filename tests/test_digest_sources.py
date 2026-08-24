"""Source selection: the ticker-search path and the named-channel path."""
import pytest

from core.models import ChannelInfo, DigestRequest
from ticker_digest.sources import SourceResolutionError, resolve_company_name, select_videos

from .digest_helpers import make_metadata


def _channel() -> ChannelInfo:
    return ChannelInfo(
        channel_id="UC" + "x" * 22,
        title="Space Investing",
        handle="@spaceinvesting",
        subscriber_count=120_000,
    )


def _request(**overrides) -> DigestRequest:
    base = {"ticker": "RKLB", "company_name": "Rocket Lab", "max_videos": 2}
    return DigestRequest(**{**base, **overrides})


# ---------------------------------------------------------------------------
# Ticker search path
# ---------------------------------------------------------------------------


def test_search_path_ranks_by_reliability_and_applies_the_limit(mocker) -> None:
    search = mocker.patch(
        "ticker_digest.sources.search_recent_videos",
        return_value=[
            make_metadata("weak", subscribers=600, views=300, duration=180, age_days=25),
            make_metadata("strong", subscribers=300_000, views=90_000, duration=1_500),
            make_metadata("middle", subscribers=20_000, views=9_000, duration=700),
        ],
    )

    videos, channel = select_videos(_request(days=14))

    assert channel is None
    assert [sv.metadata.video_id for sv in videos] == ["strong", "middle"]
    assert search.call_args.kwargs["days"] == 14
    assert search.call_args.kwargs["company_name"] == "Rocket Lab"


def test_search_path_with_no_results_returns_empty(mocker) -> None:
    mocker.patch("ticker_digest.sources.search_recent_videos", return_value=[])

    videos, channel = select_videos(_request())

    assert videos == []
    assert channel is None


# ---------------------------------------------------------------------------
# Channel path
# ---------------------------------------------------------------------------


def test_channel_path_resolves_the_channel_and_narrows_to_the_ticker(mocker) -> None:
    mocker.patch("ticker_digest.sources.resolve_channel", return_value=_channel())
    listing = mocker.patch(
        "ticker_digest.sources.list_channel_videos",
        return_value=[make_metadata("vid001"), make_metadata("vid002", views=40_000)],
    )

    videos, channel = select_videos(
        _request(source_kind="channel", channel_query="Space Investing", days=30)
    )

    assert channel is not None
    assert channel.title == "Space Investing"
    assert len(videos) == 2
    kwargs = listing.call_args.kwargs
    assert kwargs["channel_id"] == channel.channel_id
    assert kwargs["days"] == 30
    assert "RKLB" in kwargs["query"] and "Rocket Lab" in kwargs["query"]
    assert kwargs["ticker"] == "RKLB"


def test_unknown_channel_raises_rather_than_silently_searching(mocker) -> None:
    mocker.patch("ticker_digest.sources.resolve_channel", return_value=None)

    with pytest.raises(SourceResolutionError, match="No YouTube channel matched"):
        select_videos(_request(source_kind="channel", channel_query="not a real channel"))


def test_channel_kind_without_a_channel_is_a_usage_error() -> None:
    with pytest.raises(SourceResolutionError, match="no channel was given"):
        select_videos(_request(source_kind="channel"))


def test_channel_with_nothing_about_the_ticker_returns_the_channel_and_no_videos(
    mocker,
) -> None:
    mocker.patch("ticker_digest.sources.resolve_channel", return_value=_channel())
    mocker.patch("ticker_digest.sources.list_channel_videos", return_value=[])

    videos, channel = select_videos(
        _request(source_kind="channel", channel_query="Space Investing")
    )

    assert videos == []
    assert channel is not None


# ---------------------------------------------------------------------------
# Company name lookup
# ---------------------------------------------------------------------------


def test_company_name_falls_back_to_the_symbol_when_lookup_fails(mocker) -> None:
    mocker.patch(
        "core.social_media.reddit.ticker_resolver.company_name_for",
        side_effect=RuntimeError("offline"),
    )
    assert resolve_company_name("rklb") == "RKLB"


def test_company_name_uses_the_resolver_when_it_works(mocker) -> None:
    mocker.patch(
        "core.social_media.reddit.ticker_resolver.company_name_for",
        return_value="Rocket Lab USA, Inc.",
    )
    assert resolve_company_name("RKLB") == "Rocket Lab USA, Inc."
