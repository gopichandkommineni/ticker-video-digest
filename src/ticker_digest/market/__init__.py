"""Broader-market dashboard: indicator fetchers, Reality Score composite,
Claude-generated market thesis."""
from ticker_digest.market.indicators import (
    INDICATOR_REGISTRY,
    get_indicator,
    get_snapshot,
)
from ticker_digest.market.reality_score import compute_reality_score
from ticker_digest.market.thesis import generate_thesis

__all__ = [
    "INDICATOR_REGISTRY",
    "compute_reality_score",
    "generate_thesis",
    "get_indicator",
    "get_snapshot",
]
