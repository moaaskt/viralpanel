from abc import ABC, abstractmethod
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class ScrapedVideoMetadata(BaseModel):
    url: str
    platform: str = "tiktok"
    author: str
    title: str = ""
    views: int = Field(ge=0)
    likes: int = Field(ge=0)
    comments: int = Field(ge=0)
    shares: int = Field(ge=0)
    posted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    hashtags: list[str] = Field(default_factory=list)

    def to_metrics_dict(self) -> dict:
        return {
            "title": self.title,
            "views": self.views,
            "likes": self.likes,
            "comments": self.comments,
            "shares": self.shares,
            "posted_at": self.posted_at.isoformat(),
            "hashtags": self.hashtags,
        }


class BaseScraper(ABC):
    @abstractmethod
    def discover_trending(
        self,
        hashtags: list[str] | None = None,
        limit: int = 30,
    ) -> list[ScrapedVideoMetadata]:
        """Coleta os vídeos candidatos do nicho especificado."""
        raise NotImplementedError
