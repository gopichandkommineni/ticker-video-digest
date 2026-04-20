"""Pydantic models: VideoMetadata, Transcript, VideoInsights, DigestReport."""
from datetime import datetime

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
