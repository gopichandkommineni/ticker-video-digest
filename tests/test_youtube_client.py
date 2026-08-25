"""Unit tests for youtube_client — all API calls are mocked, no network."""
import pytest

from ticker_digest.youtube_client import (
    _parse_iso8601_duration,
    build_search_query,
    search_recent_videos,
)

# ---------------------------------------------------------------------------
# Fixtures — realistic but minimal API response shapes
# ---------------------------------------------------------------------------

SEARCH_RESPONSE_2_VIDEOS = {
    "items": [
        {"id": {"videoId": "vid001"}},
        {"id": {"videoId": "vid002"}},
    ]
}

VIDEOS_RESPONSE_2_VALID = {
    "items": [
        {
            "id": "vid001",
            "snippet": {
                "title": "RKLB Stock Analysis",
                "channelId": "chan_A",
                "channelTitle": "Space Investing",
                "publishedAt": "2025-01-10T12:00:00Z",
            },
            "contentDetails": {"duration": "PT8M30S"},  # 510s — passes
            "statistics": {"viewCount": "15000"},
        },
        {
            "id": "vid002",
            "snippet": {
                "title": "Rocket Lab Deep Dive",
                "channelId": "chan_A",
                "channelTitle": "Space Investing",
                "publishedAt": "2025-01-09T08:00:00Z",
            },
            "contentDetails": {"duration": "PT12M00S"},  # 720s — passes
            "statistics": {"viewCount": "8000"},
        },
    ]
}

CHANNELS_RESPONSE_CHAN_A = {
    "items": [
        {"id": "chan_A", "statistics": {"subscriberCount": "50000"}},
    ]
}


def _make_youtube_mock(mocker, search_resp, videos_resp, channels_resp):
    """Wire up the three-call mock chain and return the patched build mock."""
    mock_build = mocker.patch("ticker_digest.youtube_client.build")
    yt = mock_build.return_value
    yt.search.return_value.list.return_value.execute.return_value = search_resp
    yt.videos.return_value.list.return_value.execute.return_value = videos_resp
    yt.channels.return_value.list.return_value.execute.return_value = channels_resp
    return mock_build


# ---------------------------------------------------------------------------
# Duration parser
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw, expected",
    [
        ("PT30S", 30),
        ("PT1M", 60),
        ("PT1M30S", 90),
        ("PT1H", 3600),
        ("PT1H30M15S", 5415),
        ("PT0S", 0),
        ("PTBAD", 0),  # unrecognised → 0
    ],
)
def test_parse_iso8601_duration(raw: str, expected: int) -> None:
    assert _parse_iso8601_duration(raw) == expected


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_happy_path_returns_sorted_by_view_count(mocker) -> None:
    _make_youtube_mock(
        mocker,
        SEARCH_RESPONSE_2_VIDEOS,
        VIDEOS_RESPONSE_2_VALID,
        CHANNELS_RESPONSE_CHAN_A,
    )

    results = search_recent_videos("RKLB", "Rocket Lab")

    assert len(results) == 2
    # sorted descending by view_count
    assert results[0].view_count == 15000
    assert results[1].view_count == 8000
    assert results[0].video_id == "vid001"
    # computed url
    assert results[0].url == "https://youtube.com/watch?v=vid001"
    assert results[0].channel_subscriber_count == 50000


# ---------------------------------------------------------------------------
# Filter: short video excluded
# ---------------------------------------------------------------------------

def test_short_video_is_excluded(mocker) -> None:
    videos_resp = {
        "items": [
            {
                "id": "vid001",
                "snippet": {
                    "title": "Quick Clip",
                    "channelId": "chan_A",
                    "channelTitle": "Space Investing",
                    "publishedAt": "2025-01-10T12:00:00Z",
                },
                "contentDetails": {"duration": "PT1M"},  # 60s — below 120s threshold
                "statistics": {"viewCount": "9999"},
            },
            {
                "id": "vid002",
                "snippet": {
                    "title": "Full Analysis",
                    "channelId": "chan_A",
                    "channelTitle": "Space Investing",
                    "publishedAt": "2025-01-09T08:00:00Z",
                },
                "contentDetails": {"duration": "PT10M"},  # 600s — passes
                "statistics": {"viewCount": "5000"},
            },
        ]
    }
    _make_youtube_mock(mocker, SEARCH_RESPONSE_2_VIDEOS, videos_resp, CHANNELS_RESPONSE_CHAN_A)

    results = search_recent_videos("RKLB", "Rocket Lab")

    assert len(results) == 1
    assert results[0].video_id == "vid002"


# ---------------------------------------------------------------------------
# Filter: low-subscriber channel excluded
# ---------------------------------------------------------------------------

def test_low_sub_channel_is_excluded(mocker) -> None:
    videos_resp = {
        "items": [
            {
                "id": "vid001",
                "snippet": {
                    "title": "Big Channel Video",
                    "channelId": "chan_big",
                    "channelTitle": "Big Channel",
                    "publishedAt": "2025-01-10T12:00:00Z",
                },
                "contentDetails": {"duration": "PT8M"},
                "statistics": {"viewCount": "20000"},
            },
            {
                "id": "vid002",
                "snippet": {
                    "title": "Tiny Channel Video",
                    "channelId": "chan_tiny",
                    "channelTitle": "Tiny Channel",
                    "publishedAt": "2025-01-09T08:00:00Z",
                },
                "contentDetails": {"duration": "PT8M"},
                "statistics": {"viewCount": "50000"},
            },
        ]
    }
    channels_resp = {
        "items": [
            {"id": "chan_big", "statistics": {"subscriberCount": "10000"}},
            {"id": "chan_tiny", "statistics": {"subscriberCount": "100"}},  # below 500
        ]
    }
    _make_youtube_mock(mocker, SEARCH_RESPONSE_2_VIDEOS, videos_resp, channels_resp)

    results = search_recent_videos("RKLB", "Rocket Lab")

    assert len(results) == 1
    assert results[0].video_id == "vid001"
    assert results[0].channel_subscriber_count == 10000


# ---------------------------------------------------------------------------
# Empty search results
# ---------------------------------------------------------------------------

def test_empty_search_returns_empty_list(mocker) -> None:
    mock_build = mocker.patch("ticker_digest.youtube_client.build")
    yt = mock_build.return_value
    yt.search.return_value.list.return_value.execute.return_value = {"items": []}

    results = search_recent_videos("RKLB", "Rocket Lab")

    assert results == []
    # videos.list and channels.list should NOT be called when search is empty
    yt.videos.assert_not_called()
    yt.channels.assert_not_called()


# ---------------------------------------------------------------------------
# Query building
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "ticker, company, expected",
    [
        # Long symbols are distinctive; search for them bare.
        ("RKLB", "Rocket Lab", '"RKLB" OR "Rocket Lab" stock'),
        # Short ones are words too — lead with the company, and never let the
        # symbol appear without financial context.
        ("PL", "Planet Labs PBC", '"Planet Labs PBC" stock OR "PL stock"'),
        ("F", "Ford Motor Company", '"Ford Motor Company" stock OR "F stock"'),
        # No usable company name to lean on.
        ("RKLB", "RKLB", '"RKLB" stock'),
        ("RKLB", "", '"RKLB" stock'),
    ],
)
def test_build_search_query(ticker: str, company: str, expected: str) -> None:
    assert build_search_query(ticker, company) == expected


def test_the_search_uses_the_hedged_query(mocker) -> None:
    mock_build = _make_youtube_mock(mocker, {"items": []}, {"items": []}, {"items": []})

    search_recent_videos("PL", "Planet Labs PBC")

    query = mock_build.return_value.search.return_value.list.call_args.kwargs["q"]
    assert query == '"Planet Labs PBC" stock OR "PL stock"'
