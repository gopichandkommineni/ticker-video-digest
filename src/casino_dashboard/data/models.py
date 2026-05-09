"""Data-transfer objects for external data sources."""
from dataclasses import dataclass


@dataclass
class ApeWisdomMention:
    ticker: str
    mentions: int
    mentions_24h_ago: int | None
    upvotes: int | None
