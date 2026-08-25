"""Claude-generated market thesis from a snapshot + reality score.

Mirrors the analyzer.py pattern: ephemeral prompt caching on the system
prompt, tool-use forced via tool_choice, schema generated from the pydantic
model. Cached in SQLite by SHA256 of rounded indicator values so Streamlit
reruns don't re-spend.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

import anthropic
from pydantic import BaseModel

from core import cache
from core.models import (
    MarketRegime,
    MarketSnapshot,
    MarketThesis,
    RealityScore,
)

log = logging.getLogger(__name__)


class _ThesisSynthesis(BaseModel):
    """Fields Claude fills in. generated_at is set programmatically."""

    narrative: str
    bull_case: list[str]
    bear_case: list[str]
    key_watch_items: list[str]
    regime: MarketRegime


def _snapshot_hash(snapshot: MarketSnapshot, score: RealityScore) -> str:
    payload = {
        "score": round(score.score, 2),
        "values": {
            sid: round(ind.value, 2) if ind.value is not None else None
            for sid, ind in sorted(snapshot.indicators.items())
        },
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _extract_tool_input(response: Any, tool_name: str) -> dict[str, Any]:
    for block in response.content:
        if block.type == "tool_use" and block.name == tool_name:
            return block.input  # type: ignore[return-value]
    raise ValueError(f"No {tool_name!r} tool_use block in response")


def _format_indicators(snapshot: MarketSnapshot) -> str:
    rows: list[str] = []
    for sid, ind in snapshot.indicators.items():
        if ind.error:
            rows.append(f"- {sid} ({ind.name}): unavailable ({ind.error})")
            continue
        z_part = f", z={ind.z_score:.2f}" if ind.z_score is not None else ""
        rows.append(f"- {sid} ({ind.name}): value={ind.value:.3f}{z_part} bucket={ind.bucket}")
    return "\n".join(rows)


def generate_thesis(
    snapshot: MarketSnapshot,
    score: RealityScore,
    use_cache: bool = True,
) -> MarketThesis:
    cache_key = _snapshot_hash(snapshot, score)
    if use_cache:
        cached = cache.get_thesis(cache_key)
        if cached is not None:
            return cached

    try:
        client = anthropic.Anthropic()
    except anthropic.AnthropicError as exc:  # no credentials resolvable at all
        raise EnvironmentError(
            "The market thesis needs Claude. Set ANTHROPIC_API_KEY in .env, or "
            "sign in with `ant auth login`."
        ) from exc

    system = [
        {
            "type": "text",
            "text": (
                "You are a macro analyst synthesizing a snapshot of US market and "
                "real-economy indicators into a concise thesis.\n\n"
                "Rules:\n"
                "- The user's working hypothesis is that retail flows and sentiment "
                "have decoupled equity prices from physical-economy fundamentals. "
                "Use the data to confirm, refute, or qualify that hypothesis.\n"
                "- Reference indicators by their series id (e.g. T10Y2Y, BUFFETT) "
                "in the narrative when citing evidence.\n"
                "- Bull case and bear case must each have 3-5 bullets, drawn only "
                "from the indicators provided. Do not invent data.\n"
                "- key_watch_items are 3-5 specific releases or thresholds the user "
                "should monitor next.\n"
                "- regime is your single best label: risk_on / risk_off / neutral / "
                "fragile (fragile = mixed signals with elevated tail risk).\n"
                "- Narrative is 2-3 short paragraphs.\n\n"
                "Call the report_market_thesis tool with your synthesis."
            ),
            "cache_control": {"type": "ephemeral"},
        }
    ]

    tools = [
        {
            "name": "report_market_thesis",
            "description": "Report the synthesized broader-market thesis.",
            "input_schema": _ThesisSynthesis.model_json_schema(),
        }
    ]

    user_msg = (
        f"Snapshot timestamp: {snapshot.generated_at.isoformat()}\n"
        f"Reality Score: {score.score:+.3f} (band: {score.band})\n"
        f"Market bucket z: {score.market_z}\n"
        f"Economy bucket z: {score.economy_z}\n\n"
        f"Indicators:\n{_format_indicators(snapshot)}\n\n"
        f"Top contributions (signed z):\n"
        + "\n".join(
            f"- {sid}: {z:+.2f}"
            for sid, z in sorted(score.contributions.items(), key=lambda kv: abs(kv[1]), reverse=True)
        )
    )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=system,  # type: ignore[arg-type]
        messages=[{"role": "user", "content": user_msg}],
        tools=tools,  # type: ignore[arg-type]
        tool_choice={"type": "tool", "name": "report_market_thesis"},
    )

    synth = _ThesisSynthesis.model_validate(_extract_tool_input(response, "report_market_thesis"))
    thesis = MarketThesis(
        narrative=synth.narrative,
        bull_case=synth.bull_case,
        bear_case=synth.bear_case,
        key_watch_items=synth.key_watch_items,
        regime=synth.regime,
        generated_at=datetime.now(timezone.utc),
    )
    if use_cache:
        cache.set_thesis(cache_key, thesis)
    return thesis
