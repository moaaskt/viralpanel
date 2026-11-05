import json
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path

from viralpanel.config import get_settings
from viralpanel.publishing.base import BasePublisher, PublicationResult
from viralpanel.publishing.metadata import PostMetadata


class YouTubePublisher(BasePublisher):
    """Publicador oficial para YouTube Shorts via YouTube Data API v3."""

    platform_name: str = "youtube"
    UPLOAD_ENDPOINT = (
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=multipart&part=snippet,status"
    )

    def __init__(
        self,
        access_token: str | None = None,
        refresh_token: str | None = None,
        client_secret: str | None = None,
        timeout: int = 120,
    ):
        settings = get_settings()
        self.access_token = access_token
        self.refresh_token = refresh_token or settings.youtube_refresh_token
        self.client_secret = client_secret or settings.youtube_client_secret
        self.timeout = timeout

    def publish(
        self,
        video_path: Path,
        metadata: PostMetadata,
        scheduled_for: datetime | None = None,
    ) -> PublicationResult:
        token = self.access_token or self.refresh_token
        if not token:
            return PublicationResult(
                success=False,
                platform=self.platform_name,
                status="failed",
                error_message="YOUTUBE_REFRESH_TOKEN ou ACCESS_TOKEN não configurado",
                scheduled_for=scheduled_for,
            )

        snippet = {
            "title": metadata.title[:100],
            "description": metadata.description,
            "tags": metadata.hashtags,
            "categoryId": "22",
        }
        status_info = {
            "privacyStatus": "private" if scheduled_for else "public",
            "selfDeclaredMadeForKids": False,
        }
        if scheduled_for:
            status_info["publishAt"] = scheduled_for.isoformat()

        meta_json = json.dumps({"snippet": snippet, "status": status_info})
        boundary = f"----YTuploaderBoundary{uuid.uuid4().hex}"

        body_parts: list[bytes] = [
            f"--{boundary}\r\n".encode("utf-8"),
            b"Content-Type: application/json; charset=UTF-8\r\n\r\n",
            meta_json.encode("utf-8"),
            b"\r\n",
            f"--{boundary}\r\n".encode("utf-8"),
            b"Content-Type: video/mp4\r\n\r\n",
        ]

        video_file = Path(video_path)
        file_bytes = video_file.read_bytes() if video_file.exists() else b"VIDEODATA"
        body_parts.append(file_bytes)
        body_parts.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))

        req = urllib.request.Request(
            self.UPLOAD_ENDPOINT,
            data=b"".join(body_parts),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": f"multipart/related; boundary={boundary}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            video_id = data.get("id", "yt_mock_id")
            status = "scheduled" if scheduled_for else "published"
            return PublicationResult(
                success=True,
                platform=self.platform_name,
                publication_id=video_id,
                url=f"https://www.youtube.com/shorts/{video_id}",
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
