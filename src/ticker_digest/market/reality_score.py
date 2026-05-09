"""Composite Reality Score: how decoupled is the market from the real economy?

Pure function. No I/O. Fully unit-testable with synthetic snapshots.
"""
from __future__ import annotations

from statistics import mean

from ticker_digest import config
from ticker_digest.models import MarketSnapshot, RealityBand, RealityScore


def _band_for(score: float) -> RealityBand:
    if score >= 1.5:
        return "severe_decoupling"
    if score >= 0.5:
        return "stretched"
    if score > -0.5:
        return "aligned"
    return "market_discounting_weakness"


def compute_reality_score(
    snapshot: MarketSnapshot,
    weights: dict[str, float] | None = None,
    signs: dict[str, int] | None = None,
    buckets: dict[str, str] | None = None,
) -> RealityScore:
    weights = weights or config.REALITY_SCORE_WEIGHTS
    signs = signs or config.INDICATOR_SIGNS
    buckets = buckets or config.INDICATOR_BUCKETS

    contributions: dict[str, float] = {}
    used: list[str] = []
    skipped: list[str] = []
    market_zs: list[float] = []
    economy_zs: list[float] = []

    for series_id, indicator in snapshot.indicators.items():
        bucket = buckets.get(series_id, "context")
        if bucket == "context":
            skipped.append(series_id)
            continue
        if indicator.z_score is None:
            skipped.append(series_id)
            continue
        signed_z = signs.get(series_id, +1) * indicator.z_score
        contributions[series_id] = signed_z
        used.append(series_id)
        if bucket == "market":
            market_zs.append(signed_z)
        elif bucket == "economy":
            economy_zs.append(signed_z)

    market_z = mean(market_zs) if market_zs else None
    economy_z = mean(economy_zs) if economy_zs else None

    parts: list[float] = []
    if market_z is not None:
        parts.append(weights.get("market", 0.5) * market_z)
    if economy_z is not None:
        parts.append(weights.get("economy", 0.5) * economy_z)

    if not parts:
        # No usable indicators — return aligned/zero with full skip list.
        return RealityScore(
            score=0.0,
            band="aligned",
            market_z=None,
            economy_z=None,
            contributions={},
            used_indicators=[],
            skipped_indicators=skipped,
        )

    # Normalize when only one bucket contributes, so single-bucket runs aren't
    # half the magnitude they should be.
    if market_z is None or economy_z is None:
        denom = weights.get("market", 0.5) if economy_z is None else weights.get("economy", 0.5)
        score = parts[0] / denom if denom else parts[0]
    else:
        score = sum(parts)

    return RealityScore(
        score=round(score, 3),
        band=_band_for(score),
        market_z=round(market_z, 3) if market_z is not None else None,
        economy_z=round(economy_z, 3) if economy_z is not None else None,
        contributions={k: round(v, 3) for k, v in contributions.items()},
        used_indicators=used,
        skipped_indicators=skipped,
    )
