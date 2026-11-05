import json
import urllib.request
from datetime import datetime
from pathlib import Path

from viralpanel.config import get_settings
from viralpanel.publishing.base import BasePublisher, PublicationResult
from viralpanel.publishing.metadata import PostMetadata


class TikTokPublisher(BasePublisher):
    """Publicador oficial usando TikTok Content Posting API v2."""

    platform_name: str = "tiktok"
    INIT_ENDPOINT = "https://open.tiktokapis.com/v2/post/publish/video/init/"

    def __init__(self, access_token: str | None = None, timeout: int = 60):
        settings = get_settings()
        self.access_token = access_token or settings.tiktok_access_token
        self.timeout = timeout

    def publish(
        self,
        video_path: Path,
        metadata: PostMetadata,
        scheduled_for: datetime | None = None,
    ) -> PublicationResult:
        if not self.access_token:
            return PublicationResult(
                success=False,
                platform=self.platform_name,
                status="failed",
                error_message="TIKTOK_ACCESS_TOKEN não configurado",
                scheduled_for=scheduled_for,
            )

        video_file = Path(video_path)
        video_size = video_file.stat().st_size if video_file.exists() else 1024

        payload = {
            "post_info": {
                "title": metadata.formatted_caption[:2200],
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "disable_duet": False,
                "disable_stitch": False,
                "disable_comment": False,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": video_size,
                "chunk_size": video_size,
                "total_chunk_count": 1,
            },
        }

        req = urllib.request.Request(
            self.INIT_ENDPOINT,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json; charset=UTF-8",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            publish_id = data.get("data", {}).get("publish_id", "tt_pub_ok")
            status = "scheduled" if scheduled_for else "published"
            return PublicationResult(
                success=True,
                platform=self.platform_name,
                publication_id=publish_id,
                url=f"https://www.tiktok.com/publish/{publish_id}",
                status=status,
                scheduled_for=scheduled_for,
            )
        except Exception as exc:
            return PublicationResult(
                success=False,
                platform=self.platform_name,
                status="failed",
                error_message=str(exc),
                scheduled_for=scheduled_for,
            )

