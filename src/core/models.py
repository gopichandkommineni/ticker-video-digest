"""Pydantic models: VideoMetadata, Transcript, VideoInsights, DigestReport,
MarketIndicator, MarketSnapshot, RealityScore, MarketThesis, plus the
insight-thread shapes (ChannelInfo, ScoredVideo, Claim, ThreadPost,
InsightThread, DigestRequest, DigestRun)."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, computed_field


class VideoMetadata(BaseModel):
    video_id: str
    title: str
    channel_id: str
    channel_title: str
    channel_subscriber_count: int
    published_at: datetime
    duration_seconds: int
    view_count: int

    @computed_field  # type: ignore[prop-decorator]
    @property
    def url(self) -> str:
        return f"https://youtube.com/watch?v={self.video_id}"


class TranscriptSegment(BaseModel):
    text: str
    start_seconds: float
    duration_seconds: float


class Transcript(BaseModel):
    video_id: str
    segments: list[TranscriptSegment]
    language: str

    @property
    def full_text(self) -> str:
        return " ".join(segment.text for segment in self.segments)


Sentiment = Literal["bullish", "bearish", "neutral", "mixed"]


class Citation(BaseModel):
    video_id: str
    timestamp_seconds: int
    quote_paraphrase: str

    @computed_field  # type: ignore[prop-decorator]
    @property
    def url(self) -> str:
        return f"https://youtube.com/watch?v={self.video_id}&t={self.timestamp_seconds}s"


class VideoInsights(BaseModel):
    video_id: str
    catalysts: list[Citation]
    red_flags: list[Citation]
    upcoming_events: list[Citation]
    overall_sentiment: Sentiment
    sentiment_reasoning: str
    summary: str


class DigestReport(BaseModel):
    ticker: str
    company_name: str
    generated_at: datetime
    video_count: int
    top_catalysts: list[str]
    top_red_flags: list[str]
    upcoming_events: list[str]
    overall_sentiment: Sentiment
    synthesis: str
    video_insights: list[VideoInsights]


# ---------------------------------------------------------------------------
# Broader Market Dashboard models
# ---------------------------------------------------------------------------

IndicatorSource = Literal["fred", "yfinance", "computed", "scrape"]
IndicatorBucket = Literal["market", "economy", "context"]
RealityBand = Literal[
    "market_discounting_weakness",
    "aligned",
    "stretched",
    "severe_decoupling",
]
MarketRegime = Literal["risk_on", "risk_off", "neutral", "fragile"]


class MarketIndicator(BaseModel):
    name: str
    series_id: str
    source: IndicatorSource
    bucket: IndicatorBucket
    value: float | None = None
    z_score: float | None = None
    as_of: datetime | None = None
    history: dict[str, float] = Field(default_factory=dict)
    error: str | None = None


class MarketSnapshot(BaseModel):
    generated_at: datetime
    indicators: dict[str, MarketIndicator]


class RealityScore(BaseModel):
    score: float
    band: RealityBand
    market_z: float | None
    economy_z: float | None
    contributions: dict[str, float] = Field(default_factory=dict)
    used_indicators: list[str] = Field(default_factory=list)
    skipped_indicators: list[str] = Field(default_factory=list)


class MarketThesis(BaseModel):
    narrative: str
    bull_case: list[str]
    bear_case: list[str]
    key_watch_items: list[str]
    regime: MarketRegime
    generated_at: datetime


# ---------------------------------------------------------------------------
# YouTube insight-thread models (ticker_digest)
# ---------------------------------------------------------------------------

# How a digest run picked its videos: a YouTube search for the ticker, or a
# specific channel the user nominated.
SourceKind = Literal["ticker_search", "channel"]

# What kind of claim a Citation carries once it has been lifted out of a
# per-video extraction and tracked across runs.
ClaimKind = Literal["catalyst", "red_flag", "upcoming_event"]

# Is this claim actually news? "new" = not seen in any earlier run for this
# ticker; "developing" = an update to something already tracked; "known" =
# a restatement of an existing claim.
Novelty = Literal["new", "developing", "known"]

DISCLAIMER = (
    "Aggregated commentary from public YouTube videos. Not investment advice."
)


class ChannelInfo(BaseModel):
    """A YouTube channel resolved from a name, handle, URL or channel id."""

    channel_id: str
    title: str
    handle: str | None = None
    subscriber_count: int = 0
    video_count: int = 0
    view_count: int = 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def url(self) -> str:
        return f"https://youtube.com/channel/{self.channel_id}"


class ScoredVideo(BaseModel):
    """A candidate video plus the reliability score that ranked it."""

    metadata: VideoMetadata
    reliability_score: float
    score_components: dict[str, float] = Field(default_factory=dict)


class Claim(BaseModel):
    """One extracted claim, tracked across runs so novelty can be judged.

    A claim holds *every* citation that supports it, not just the first. Three
    videos reporting one contract award are one claim with three citations —
    and how many independent sources said a thing is the strongest signal the
    thread has.
    """

    ticker: str
    kind: ClaimKind
    text: str
    citations: list[Citation]
    fingerprint: str
    novelty: Novelty = "new"
    novelty_reasoning: str = ""
    related_claim: str | None = None
    # True when a claim already on record was repeated this run by a channel
    # that had never said it before: the claim is old, the agreement is new.
    newly_corroborated: bool = False
    first_seen_at: datetime | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def source_count(self) -> int:
        """Distinct videos backing this claim — not citations, videos."""
        return len({citation.video_id for citation in self.citations})


class ThreadPost(BaseModel):
    """One post in the generated insight thread."""

    position: int
    headline: str
    body: str
    novelty: Novelty
    citations: list[Citation] = Field(default_factory=list)


class InsightThread(BaseModel):
    """The stored deliverable: a thread of insights across analysed videos."""

    thread_id: str
    ticker: str
    company_name: str
    source_kind: SourceKind
    source_label: str
    generated_at: datetime
    video_count: int
    new_claim_count: int
    overall_sentiment: Sentiment
    headline: str
    posts: list[ThreadPost]
    disclaimer: str = DISCLAIMER


class DigestRequest(BaseModel):
    """What the user asked for: a ticker, and where to look for videos."""

    ticker: str
    company_name: str
    source_kind: SourceKind = "ticker_search"
    channel_query: str | None = None
    days: int = 7
    max_videos: int = 5


class DigestRun(BaseModel):
    """Everything one end-to-end run produced, stored and returned to the CLI."""

    run_id: str
    request: DigestRequest
    generated_at: datetime
    channel: ChannelInfo | None = None
    videos: list[ScoredVideo] = Field(default_factory=list)
    insights: list[VideoInsights] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    thread: InsightThread | None = None
    skipped: dict[str, str] = Field(default_factory=dict)
