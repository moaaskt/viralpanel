import json
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

from viralpanel.config import get_settings
from viralpanel.publishing.base import BasePublisher, PublicationResult
from viralpanel.publishing.metadata import PostMetadata


class InstagramPublisher(BasePublisher):
    """Publicador oficial para Instagram Reels via Meta Graph API oficial."""

    platform_name: str = "instagram"
    GRAPH_API_BASE = "https://graph.facebook.com/v21.0"

    def __init__(
        self,
        access_token: str | None = None,
        account_id: str | None = None,
        timeout: int = 60,
    ):
        settings = get_settings()
        self.access_token = access_token or settings.instagram_access_token
        self.account_id = account_id or settings.instagram_account_id
        self.timeout = timeout

    def publish(
        self,
        video_path: Path,
        metadata: PostMetadata,
        scheduled_for: datetime | None = None,
    ) -> PublicationResult:
        if not self.access_token or not self.account_id:
            return PublicationResult(
                success=False,
                platform=self.platform_name,
                status="failed",
                error_message="INSTAGRAM_ACCESS_TOKEN ou INSTAGRAM_ACCOUNT_ID não configurados",
                scheduled_for=scheduled_for,
            )

        container_url = f"{self.GRAPH_API_BASE}/{self.account_id}/media"
        container_params = {
            "media_type": "REELS",
            "caption": metadata.formatted_caption[:2200],
            "access_token": self.access_token,
        }
        if scheduled_for:
            container_params["scheduled_publish_time"] = int(scheduled_for.timestamp())

        try:
            # 1. Cria container de Reels
            data_encoded = urllib.parse.urlencode(container_params).encode("utf-8")
            req = urllib.request.Request(container_url, data=data_encoded, method="POST")
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                container_data = json.loads(resp.read().decode("utf-8"))
            creation_id = container_data.get("id")

            # 2. Publica o container (se não for agendamento futuro gerido pela Meta)
            publish_url = f"{self.GRAPH_API_BASE}/{self.account_id}/media_publish"
            publish_params = {"creation_id": creation_id, "access_token": self.access_token}
            req_pub = urllib.request.Request(
                publish_url,
                data=urllib.parse.urlencode(publish_params).encode("utf-8"),
                method="POST",
            )
            with urllib.request.urlopen(req_pub, timeout=self.timeout) as resp_pub:
                pub_data = json.loads(resp_pub.read().decode("utf-8"))

            media_id = pub_data.get("id", creation_id)
            status = "scheduled" if scheduled_for else "published"
            return PublicationResult(
                success=True,
                platform=self.platform_name,
                publication_id=media_id,
                url=f"https://www.instagram.com/reel/{media_id}/",
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
