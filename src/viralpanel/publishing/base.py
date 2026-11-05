from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from viralpanel.publishing.metadata import PostMetadata


class PublicationResult(BaseModel):
    success: bool
    platform: str
    publication_id: str | None = None
    url: str | None = None
    status: str = "published"  # 'published', 'scheduled', or 'failed'
    error_message: str | None = None
    scheduled_for: datetime | None = None


class BasePublisher(ABC):
    platform_name: str

    @abstractmethod
    def publish(
        self,
        video_path: Path,
        metadata: PostMetadata,
        scheduled_for: datetime | None = None,
    ) -> PublicationResult:
        """Publica ou agenda o vídeo na plataforma e retorna PublicationResult."""
        raise NotImplementedError


class MockPublisher(BasePublisher):
    """Publicador determinístico em memória para testes e execução local offline."""

    def __init__(self, platform_name: str = "mock"):
        self.platform_name = platform_name
        self.published_items: list[dict] = []

    def publish(
        self,
        video_path: Path,
        metadata: PostMetadata,
        scheduled_for: datetime | None = None,
    ) -> PublicationResult:
        idx = len(self.published_items) + 1
        plat = self.platform_name.lower()
        if plat == "tiktok":
            fake_url = f"https://www.tiktok.com/@creator/video/{1000000000 + idx}"
        elif plat == "instagram":
            fake_url = f"https://www.instagram.com/reel/C{idx}viral{idx}/"
        elif plat == "youtube":
            fake_url = f"https://www.youtube.com/shorts/mock_yt_{idx}"
        else:
            fake_url = f"https://{plat}.example.com/posts/{idx}"

        status = "scheduled" if scheduled_for else "published"
        entry = {
            "video_path": str(video_path),
            "metadata": metadata.model_dump(),
            "scheduled_for": scheduled_for.isoformat() if scheduled_for else None,
            "url": fake_url,
            "status": status,
        }
        self.published_items.append(entry)

        return PublicationResult(
            success=True,
            platform=self.platform_name,
            publication_id=f"{plat}-pub-{idx}",
            url=fake_url,
            status=status,
            scheduled_for=scheduled_for,
        )

