"""Abstract base class and shared data models for all social media scrapers."""
from abc import ABC, abstractmethod
from datetime import datetime

from pydantic import BaseModel, Field


class SocialPost(BaseModel):
    platform: str
    post_id: str
    author: str
    title: str | None = None  # present on Reddit, absent on X
    content: str
    url: str
    published_at: datetime
    score: int = 0           # upvotes on Reddit, likes on X
    comment_count: int = 0
    ticker: str
    subreddit: str | None = None  # Reddit-specific


class SocialSignals(BaseModel):
    ticker: str
    platform: str
    posts: list[SocialPost] = Field(default_factory=list)
    fetched_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def total_posts(self) -> int:
        return len(self.posts)

    @property
    def avg_score(self) -> float:
        if not self.posts:
            return 0.0
        return sum(p.score for p in self.posts) / len(self.posts)

    @property
    def top_posts(self) -> list[SocialPost]:
        return sorted(self.posts, key=lambda p: p.score, reverse=True)[:10]


class SocialScraper(ABC):
    """Base class for all social media platform scrapers.

    To add a new platform, subclass this, implement `platform_name` and
    `search_ticker`, then register the scraper in social_media/__init__.py.
    """

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Human-readable platform identifier, e.g. 'reddit' or 'x'."""

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Return True only when the required credentials are configured."""

    @abstractmethod
    def search_ticker(
        self,
        ticker: str,
        days_back: int = 7,
        max_posts: int = 50,
    ) -> SocialSignals:
        """Fetch recent posts mentioning *ticker* and return structured signals."""
