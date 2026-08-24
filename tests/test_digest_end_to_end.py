"""End-to-end digest with only the outside world mocked.

Everything between the YouTube API, the caption API and the Anthropic API runs
for real — source selection, quality filtering, transcript caching, claim
extraction, novelty, thread building and SQLite storage. This is the test that
catches wiring mistakes the per-module tests can't see.
"""
from unittest.mock import MagicMock

import pytest
from youtube_transcript_api._errors import TranscriptsDisabled

from core.models import DigestRequest
from ticker_digest import store
from ticker_digest.pipeline import run_digest

from .digest_helpers import tool_response

CHANNEL_ID = "UC" + "a" * 22

SEARCH_RESPONSE = {"items": [{"id": {"videoId": "vid001"}}, {"id": {"videoId": "vid002"}}]}

VIDEOS_RESPONSE = {
    "items": [
        {
            "id": "vid001",
            "snippet": {
                "title": "Rocket Lab Q3 breakdown",
                "channelId": CHANNEL_ID,
                "channelTitle": "Space Investing",
                "publishedAt": "2026-08-22T12:00:00Z",
            },
            "contentDetails": {"duration": "PT18M"},
            "statistics": {"viewCount": "22000"},
        },
        {
            "id": "vid002",
            "snippet": {
                "title": "RKLB TO THE MOON RIGHT NOW 🚀🔥",
                "channelId": CHANNEL_ID,
                "channelTitle": "Space Investing",
                "publishedAt": "2026-08-21T12:00:00Z",
            },
            "contentDetails": {"duration": "PT9M"},
            "statistics": {"viewCount": "99000"},
        },
    ]
}

CHANNEL_STATS = {"items": [{"id": CHANNEL_ID, "statistics": {"subscriberCount": "120000"}}]}

EXTRACTION = {
    "video_id": "vid001",
    "catalysts": [
        {
            "video_id": "vid001",
            "timestamp_seconds": 42,
            "quote_paraphrase": "Neutron rocket first launch scheduled for Q4 2026",
        }
    ],
    "red_flags": [],
    "upcoming_events": [],
    "overall_sentiment": "bullish",
    "sentiment_reasoning": "Positive on the launch timeline.",
    "summary": "Bullish on Neutron's timeline.",
}

THREAD_DRAFT = {
    "headline": "Rocket Lab: a firm Neutron date, finally",
    "overall_sentiment": "bullish",
    "posts": [
        {
            "headline": "Neutron launch pinned to Q4",
            "body": "One commentator gave a specific quarter for the first flight.",
            "novelty": "new",
            "citations": [
                {
                    "video_id": "vid001",
                    "timestamp_seconds": 42,
                    "quote_paraphrase": "Neutron rocket first launch scheduled for Q4 2026",
                },
                {
                    "video_id": "invented",
                    "timestamp_seconds": 5,
                    "quote_paraphrase": "Never said",
                },
            ],
        }
    ],
}


NOVELTY_CLASSIFICATION = {
    "classifications": [
        {
            "index": 0,
            "novelty": "developing",
            "reasoning": "Adds a quarter to a tracked launch.",
            "related_claim": "Neutron rocket first launch scheduled for Q4 2026",
        }
    ]
}


@pytest.fixture
def wired(mocker, tmp_path, monkeypatch):
    """Mock only the three external services, and isolate both caches.

    All three modules share one ``anthropic`` module object, so there is one
    fake client for the lot; it answers based on which tool the caller forced.
    """
    monkeypatch.setenv("TICKER_DIGEST_CACHE_DIR", str(tmp_path / "cache"))

    build = mocker.patch("ticker_digest.youtube_client.build")
    yt = build.return_value
    yt.search.return_value.list.return_value.execute.return_value = SEARCH_RESPONSE
    yt.videos.return_value.list.return_value.execute.return_value = VIDEOS_RESPONSE
    yt.channels.return_value.list.return_value.execute.return_value = CHANNEL_STATS

    snippet = MagicMock()
    snippet.text = "Neutron is scheduled for the fourth quarter."
    snippet.start = 42.0
    snippet.duration = 3.0
    fetched = MagicMock()
    fetched.snippets = [snippet]
    fetched.language_code = "en"
    captions = mocker.patch("ticker_digest.transcripts.YouTubeTranscriptApi")
    captions.return_value.fetch.return_value = fetched

    payloads = {
        "report_video_insights": EXTRACTION,
        "report_thread": THREAD_DRAFT,
        "classify_claims": NOVELTY_CLASSIFICATION,
    }
    calls: dict[str, int] = {name: 0 for name in payloads}

    def _create(**kwargs):
        tool_name = kwargs["tools"][0]["name"]
        calls[tool_name] += 1
        return tool_response(tool_name, payloads[tool_name])

    client = MagicMock()
    client.messages.create.side_effect = _create
    mocker.patch("anthropic.Anthropic", return_value=client)

    return {
        "db": tmp_path / "digests.db",
        "youtube": yt,
        "captions": captions,
        "calls": calls,
        "payloads": payloads,
    }


def _request() -> DigestRequest:
    return DigestRequest(ticker="RKLB", company_name="Rocket Lab", max_videos=5)


def test_first_run_produces_a_stored_thread(wired) -> None:
    run = run_digest(_request(), db_path=wired["db"])

    # The bait-titled video was filtered out before any transcript was fetched.
    assert [sv.metadata.video_id for sv in run.videos] == ["vid001"]

    assert len(run.claims) == 1
    assert run.claims[0].novelty == "new"
    assert run.claims[0].text == "Neutron rocket first launch scheduled for Q4 2026"

    assert run.thread is not None
    assert run.thread.new_claim_count == 1
    # The invented citation never reaches the reader.
    assert [c.video_id for c in run.thread.posts[0].citations] == ["vid001"]

    stored = store.get_thread(run.thread.thread_id, db_path=wired["db"])
    assert stored is not None
    assert stored.headline == "Rocket Lab: a firm Neutron date, finally"

    # No history existed, so nothing was sent for novelty judging.
    assert wired["calls"]["classify_claims"] == 0


def test_second_run_sees_the_first_run_as_history(wired) -> None:
    run_digest(_request(), db_path=wired["db"])
    second = run_digest(_request(), db_path=wired["db"])

    # Identical claim text — caught deterministically, still no model call.
    assert second.claims[0].novelty == "known"
    assert wired["calls"]["classify_claims"] == 0


def test_a_changed_claim_reaches_the_novelty_model(wired) -> None:
    run_digest(_request(), db_path=wired["db"])

    wired["payloads"]["report_video_insights"] = {
        **EXTRACTION,
        "catalysts": [
            {
                "video_id": "vid001",
                "timestamp_seconds": 90,
                "quote_paraphrase": "Wallops pad lease signed for the Virginia launch site",
            }
        ],
    }

    second = run_digest(_request(), db_path=wired["db"])

    assert second.claims[0].novelty == "developing"
    assert wired["calls"]["classify_claims"] == 1
    assert len(store.known_claims("RKLB", db_path=wired["db"])) == 2


def test_a_video_without_captions_is_skipped_not_fatal(wired) -> None:
    wired["captions"].return_value.fetch.side_effect = TranscriptsDisabled("vid001")

    run = run_digest(_request(), db_path=wired["db"])

    assert run.skipped == {"vid001": "no captions available"}
    assert run.thread is None
    assert store.list_threads(db_path=wired["db"]) == []
