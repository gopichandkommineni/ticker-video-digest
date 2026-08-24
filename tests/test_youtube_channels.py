"""Channel resolution and channel listing — YouTube API calls are mocked."""
from ticker_digest.youtube_client import list_channel_videos, resolve_channel

CHANNEL_ID = "UC" + "a" * 22

CHANNEL_RESPONSE = {
    "items": [
        {
            "id": CHANNEL_ID,
            "snippet": {"title": "Space Investing", "customUrl": "@spaceinvesting"},
            "statistics": {
                "subscriberCount": "120000",
                "videoCount": "430",
                "viewCount": "9000000",
            },
        }
    ]
}

VIDEOS_RESPONSE = {
    "items": [
        {
            "id": "vid001",
            "snippet": {
                "title": "Rocket Lab Q3 breakdown",
                "channelId": CHANNEL_ID,
                "channelTitle": "Space Investing",
                "publishedAt": "2026-04-18T12:00:00Z",
            },
            "contentDetails": {"duration": "PT18M"},
            "statistics": {"viewCount": "22000"},
        },
        {
            "id": "vid002",
            "snippet": {
                "title": "RKLB IS ABOUT TO EXPLODE 🚀🔥",
                "channelId": CHANNEL_ID,
                "channelTitle": "Space Investing",
                "publishedAt": "2026-04-17T12:00:00Z",
            },
            "contentDetails": {"duration": "PT9M"},
            "statistics": {"viewCount": "90000"},
        },
    ]
}

CHANNEL_STATS_RESPONSE = {
    "items": [{"id": CHANNEL_ID, "statistics": {"subscriberCount": "120000"}}]
}


def _youtube(mocker, *, search=None, videos=None, channels=None):
    build = mocker.patch("ticker_digest.youtube_client.build")
    yt = build.return_value
    yt.search.return_value.list.return_value.execute.return_value = search or {"items": []}
    yt.videos.return_value.list.return_value.execute.return_value = videos or {"items": []}
    yt.channels.return_value.list.return_value.execute.return_value = channels or {"items": []}
    return yt


# ---------------------------------------------------------------------------
# resolve_channel
# ---------------------------------------------------------------------------


def test_resolves_a_bare_channel_id_without_searching(mocker) -> None:
    yt = _youtube(mocker, channels=CHANNEL_RESPONSE)

    channel = resolve_channel(CHANNEL_ID)

    assert channel is not None
    assert channel.title == "Space Investing"
    assert channel.handle == "@spaceinvesting"
    assert channel.subscriber_count == 120_000
    assert channel.url == f"https://youtube.com/channel/{CHANNEL_ID}"
    yt.search.assert_not_called()


def test_resolves_a_channel_url(mocker) -> None:
    yt = _youtube(mocker, channels=CHANNEL_RESPONSE)

    channel = resolve_channel(f"https://www.youtube.com/channel/{CHANNEL_ID}/videos")

    assert channel is not None and channel.channel_id == CHANNEL_ID
    yt.search.assert_not_called()


def test_resolves_a_handle_via_for_handle(mocker) -> None:
    yt = _youtube(mocker, channels=CHANNEL_RESPONSE)

    channel = resolve_channel("@spaceinvesting")

    assert channel is not None and channel.channel_id == CHANNEL_ID
    assert yt.channels.return_value.list.call_args.kwargs["forHandle"] == "@spaceinvesting"
    yt.search.assert_not_called()


def test_falls_back_to_a_name_search(mocker) -> None:
    yt = _youtube(
        mocker,
        search={"items": [{"id": {"channelId": CHANNEL_ID}, "snippet": {}}]},
        channels=CHANNEL_RESPONSE,
    )

    channel = resolve_channel("Space Investing")

    assert channel is not None and channel.channel_id == CHANNEL_ID
    assert yt.search.return_value.list.call_args.kwargs["type"] == "channel"


def test_unmatched_name_returns_none(mocker) -> None:
    _youtube(mocker, search={"items": []})

    assert resolve_channel("channel that does not exist") is None


def test_blank_query_returns_none_without_calling_the_api(mocker) -> None:
    build = mocker.patch("ticker_digest.youtube_client.build")

    assert resolve_channel("   ") is None
    build.assert_not_called()


def test_handle_lookup_failure_falls_back_to_search(mocker) -> None:
    build = mocker.patch("ticker_digest.youtube_client.build")
    yt = build.return_value
    yt.channels.return_value.list.return_value.execute.side_effect = [
        TypeError("forHandle is not supported"),
        CHANNEL_RESPONSE,
    ]
    yt.search.return_value.list.return_value.execute.return_value = {
        "items": [{"id": {"channelId": CHANNEL_ID}, "snippet": {}}]
    }

    channel = resolve_channel("@spaceinvesting")

    assert channel is not None and channel.channel_id == CHANNEL_ID


# ---------------------------------------------------------------------------
# list_channel_videos
# ---------------------------------------------------------------------------


def test_channel_listing_filters_bait_and_sorts_newest_first(mocker) -> None:
    yt = _youtube(
        mocker,
        search={"items": [{"id": {"videoId": "vid001"}}, {"id": {"videoId": "vid002"}}]},
        videos=VIDEOS_RESPONSE,
        channels=CHANNEL_STATS_RESPONSE,
    )

    videos = list_channel_videos(CHANNEL_ID, days=30, query="RKLB", ticker="RKLB")

    # vid002 has more views but an all-caps, emoji-stuffed title.
    assert [v.video_id for v in videos] == ["vid001"]
    params = yt.search.return_value.list.call_args.kwargs
    assert params["channelId"] == CHANNEL_ID
    assert params["q"] == "RKLB"
    assert "publishedAfter" in params


def test_channel_listing_omits_the_query_when_none_is_given(mocker) -> None:
    yt = _youtube(mocker, search={"items": []})

    assert list_channel_videos(CHANNEL_ID) == []
    assert "q" not in yt.search.return_value.list.call_args.kwargs
    yt.videos.assert_not_called()
