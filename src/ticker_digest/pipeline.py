"""End-to-end digest: source selection → transcripts → LLM → novelty → thread.

This is the only module that knows the whole sequence. Each step it calls is
independently testable; this one wires them together and decides what happens
when a step fails for one video (skip it and say why — never fail the run).
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

import anthropic

from core.models import Claim, DigestRequest, DigestRun, VideoInsights
from ticker_digest import store
from ticker_digest.analyzer import extract_insights
from ticker_digest.llm import LLMUnavailableError
from ticker_digest.novelty import assess, claims_from_insights, rank_claims
from ticker_digest.sources import select_videos
from ticker_digest.thread import build_thread
from ticker_digest.transcripts import get_transcript

log = logging.getLogger(__name__)


class DigestSetupError(RuntimeError):
    """The run can't proceed because of how it's configured, not what it found."""


def _run_id(ticker: str, generated_at: datetime, source_label: str) -> str:
    seed = f"run|{ticker.upper()}|{generated_at.isoformat()}|{source_label}"
    return hashlib.sha1(seed.encode()).hexdigest()[:12]


def mark_corroboration(
    claims: list[Claim],
    known_channels: dict[str, set[str]],
    channel_by_video: dict[str, str],
) -> list[Claim]:
    """Flag already-tracked claims that a *new* channel just repeated.

    The claim is old; the agreement is what changed. Counting channels rather
    than videos is deliberate — one commentator posting three times is one
    source, not three.

    Two cases stay unflagged: a claim nothing on record covers (it's already
    ``new``), and a claim whose recorded history predates channel tracking. In
    the second case we genuinely cannot tell, and saying "newly corroborated"
    when we don't know would be a lie the reader can't check.
    """
    marked: list[Claim] = []
    for claim in claims:
        previous = known_channels.get(claim.fingerprint, set())
        if claim.novelty == "new" or not previous or store.UNKNOWN_CHANNEL in previous:
            marked.append(claim)
            continue
        this_run = {
            channel_by_video.get(citation.video_id, store.UNKNOWN_CHANNEL)
            for citation in claim.citations
        }
        fresh = {channel for channel in this_run if channel and channel not in previous}
        marked.append(claim.model_copy(update={"newly_corroborated": bool(fresh)}))
    return marked


def run_digest(
    request: DigestRequest,
    db_path: Path | None = None,
    persist: bool = True,
) -> DigestRun:
    """Run one digest and return everything it produced.

    A run with no usable videos is still a valid run: it comes back with an
    empty thread and the reasons each candidate was dropped, which is more
    useful than an exception.
    """
    generated_at = datetime.now(timezone.utc)
    ticker = request.ticker.upper()

    videos, channel = select_videos(request)
    source_label = channel.title if channel else ticker
    run_id = _run_id(ticker, generated_at, source_label)

    skipped: dict[str, str] = {}
    insights: list[VideoInsights] = []

    for scored in videos:
        video_id = scored.metadata.video_id
        transcript = get_transcript(video_id)
        if transcript is None:
            skipped[video_id] = "no captions available"
            continue
        try:
            insights.append(extract_insights(transcript, scored.metadata))
        except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as exc:
            # Not a bad video — a bad key. Every remaining video would fail the
            # same way, so stop instead of paying to find that out N times.
            raise DigestSetupError(
                "Claude rejected the request: "
                f"{getattr(exc, 'message', str(exc))}\n"
                "  Check ANTHROPIC_API_KEY in .env is a real key, not a placeholder."
            ) from exc
        except LLMUnavailableError as exc:
            # Same reasoning, for the Claude Code CLI path.
            raise DigestSetupError(str(exc)) from exc
        except Exception as exc:  # noqa: BLE001 — one bad video must not kill the run
            log.warning("Extraction failed for %s: %s", video_id, exc)
            skipped[video_id] = f"extraction failed: {exc}"

    analysed = [sv for sv in videos if sv.metadata.video_id not in skipped]

    claims = claims_from_insights(ticker, insights)
    # Both reads must happen before this run is saved, or it would be judged
    # against itself.
    known = store.known_claims(ticker, db_path=db_path)
    known_channels = store.known_claim_channels(ticker, db_path=db_path)

    judged = assess(ticker, request.company_name, claims, known)
    channel_by_video = {
        scored.metadata.video_id: scored.metadata.channel_id for scored in videos
    }
    judged = rank_claims(mark_corroboration(judged, known_channels, channel_by_video))
    for claim in judged:
        claim.first_seen_at = generated_at

    thread = None
    if insights:
        thread = build_thread(
            ticker=ticker,
            company_name=request.company_name,
            claims=judged,
            insights=insights,
            videos=analysed,
            source_kind=request.source_kind,
            source_label=source_label,
            generated_at=generated_at,
        )
    else:
        log.warning("No videos yielded insights for %s — no thread generated", ticker)

    run = DigestRun(
        run_id=run_id,
        request=request,
        generated_at=generated_at,
        channel=channel,
        videos=videos,
        insights=insights,
        claims=judged,
        thread=thread,
        skipped=skipped,
    )

    if persist:
        store.save_run(run, db_path=db_path)

    return run
