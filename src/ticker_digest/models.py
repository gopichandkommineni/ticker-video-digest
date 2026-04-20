"""Pydantic models: VideoMetadata, Transcript, VideoInsights, DigestReport."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, computed_field


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
