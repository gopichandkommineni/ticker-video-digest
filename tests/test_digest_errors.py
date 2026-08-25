"""Predictable failures must read as instructions, not stack traces."""
from unittest.mock import MagicMock

import anthropic
import pytest
from googleapiclient.errors import HttpError

from core.models import DigestRequest
from ticker_digest.cli import main
from ticker_digest.pipeline import DigestSetupError, run_digest
from ticker_digest.quality import score_videos
from ticker_digest.youtube_client import YouTubeAccessError, search_recent_videos

from .digest_helpers import NOW, make_insights, make_metadata


def _http_error(status: int, reason: str, message: str) -> HttpError:
    resp = MagicMock()
    resp.status = status
    resp.reason = message
    error = HttpError(resp, b"{}")
    error.error_details = [{"reason": reason, "message": message}]
    return error


def _youtube_raising(mocker, error: HttpError):
    build = mocker.patch("ticker_digest.youtube_client.build")
    build.return_value.search.return_value.list.return_value.execute.side_effect = error
    return build


# ---------------------------------------------------------------------------
# YouTube
# ---------------------------------------------------------------------------


def test_a_placeholder_api_key_names_the_setting_to_fix(mocker) -> None:
    _youtube_raising(
        mocker,
        _http_error(400, "badRequest", "API key not valid. Please pass a valid API key."),
    )

    with pytest.raises(YouTubeAccessError) as caught:
        search_recent_videos("RKLB", "Rocket Lab")

    message = str(caught.value)
    assert "YOUTUBE_API_KEY" in message
    assert "YouTube Data API v3" in message


def test_exhausted_quota_says_so_and_says_when_it_returns(mocker) -> None:
    _youtube_raising(mocker, _http_error(403, "quotaExceeded", "Quota exceeded"))

    with pytest.raises(YouTubeAccessError) as caught:
        search_recent_videos("RKLB", "Rocket Lab")

    message = str(caught.value)
    assert "quota" in message.lower()
    assert "midnight Pacific" in message
    # The quota message must not send the reader off to check their key.
    assert "YOUTUBE_API_KEY" not in message


def test_an_unrecognised_http_error_is_left_alone(mocker) -> None:
    """Only the failures we can give advice about get rewritten."""
    _youtube_raising(mocker, _http_error(500, "backendError", "Internal error"))

    with pytest.raises(HttpError):
        search_recent_videos("RKLB", "Rocket Lab")


def test_the_cli_prints_the_advice_and_exits_one(mocker, capsys) -> None:
    mocker.patch("ticker_digest.sources.resolve_company_name", return_value="Rocket Lab")
    mocker.patch(
        "ticker_digest.pipeline.run_digest",
        side_effect=YouTubeAccessError("YOUTUBE_API_KEY looks wrong"),
    )

    assert main(["ticker", "RKLB"]) == 1
    err = capsys.readouterr().err
    assert "YOUTUBE_API_KEY looks wrong" in err
    assert "Traceback" not in err


# ---------------------------------------------------------------------------
# Anthropic
# ---------------------------------------------------------------------------


def test_a_rejected_claude_key_stops_the_run_instead_of_retrying_per_video(
    mocker, tmp_path
) -> None:
    scored = score_videos([make_metadata("vid001"), make_metadata("vid002")], now=NOW)
    mocker.patch("ticker_digest.pipeline.select_videos", return_value=(scored, None))
    mocker.patch("ticker_digest.pipeline.get_transcript", return_value=mocker.MagicMock())

    auth_error = anthropic.AuthenticationError(
        message="invalid x-api-key",
        response=MagicMock(status_code=401, headers={}),
        body=None,
    )
    extract = mocker.patch(
        "ticker_digest.pipeline.extract_insights", side_effect=auth_error
    )

    with pytest.raises(DigestSetupError) as caught:
        run_digest(
            DigestRequest(ticker="RKLB", company_name="Rocket Lab"),
            db_path=tmp_path / "d.db",
        )

    assert "ANTHROPIC_API_KEY" in str(caught.value)
    # Stopped on the first video rather than paying to fail on the second.
    assert extract.call_count == 1


def test_an_ordinary_extraction_failure_still_only_skips_that_video(
    mocker, tmp_path
) -> None:
    scored = score_videos([make_metadata("vid001"), make_metadata("vid002")], now=NOW)
    mocker.patch("ticker_digest.pipeline.select_videos", return_value=(scored, None))
    mocker.patch("ticker_digest.pipeline.get_transcript", return_value=mocker.MagicMock())
    mocker.patch(
        "ticker_digest.pipeline.extract_insights",
        side_effect=[RuntimeError("model hiccup"), make_insights("vid002")],
    )
    mocker.patch("ticker_digest.pipeline.claims_from_insights", return_value=[])
    mocker.patch("ticker_digest.pipeline.assess", return_value=[])
    mocker.patch("ticker_digest.pipeline.build_thread", return_value=None)

    run = run_digest(
        DigestRequest(ticker="RKLB", company_name="Rocket Lab"),
        db_path=tmp_path / "d.db",
        persist=False,
    )

    assert "extraction failed" in run.skipped["vid001"]
    assert len(run.insights) == 1
