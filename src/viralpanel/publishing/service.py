from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from viralpanel.models import Asset, Publication, Script
from viralpanel.publishing.auth import PlatformCredentials
from viralpanel.publishing.base import BasePublisher, MockPublisher
from viralpanel.publishing.instagram import InstagramPublisher
from viralpanel.publishing.metadata import MetadataGenerator
from viralpanel.publishing.tiktok import TikTokPublisher
from viralpanel.publishing.youtube import YouTubePublisher
from viralpanel.telegram.notifier import TelegramNotifier


class PublishingService:
    """Orquestra a publicação multiplataforma (TikTok, Instagram Reels, YouTube Shorts)."""

    def __init__(
        self,
        publishers: dict[str, BasePublisher] | None = None,
        metadata_generator: MetadataGenerator | None = None,
        notifier: TelegramNotifier | None = None,
    ):
        self.metadata_generator = metadata_generator or MetadataGenerator()
        self.notifier = notifier
        self.publishers = publishers or self._build_default_publishers()

    def _build_default_publishers(self) -> dict[str, BasePublisher]:
        creds = PlatformCredentials.from_settings()
        pubs: dict[str, BasePublisher] = {}
        if creds.is_platform_configured("tiktok"):
            pubs["tiktok"] = TikTokPublisher()
        else:
            pubs["tiktok"] = MockPublisher("tiktok")

        if creds.is_platform_configured("instagram"):
            pubs["instagram"] = InstagramPublisher()
        else:
            pubs["instagram"] = MockPublisher("instagram")

        if creds.is_platform_configured("youtube"):
            pubs["youtube"] = YouTubePublisher()
        else:
            pubs["youtube"] = MockPublisher("youtube")

        return pubs

    def publish_asset(
        self,
        db: Session,
        asset: Asset,
        script: Script,
        scheduled_for: datetime | None = None,
    ) -> list[Publication]:
        video_path = Path(asset.file_path)
        persisted_publications: list[Publication] = []
        published_links: list[str] = []

        for platform, publisher in self.publishers.items():
            metadata = self.metadata_generator.generate(script=script, platform=platform)
            res = publisher.publish(
                video_path=video_path,
                metadata=metadata,
                scheduled_for=scheduled_for,
            )

            now_utc = datetime.now(timezone.utc)
            pub_record = Publication(
                asset_id=asset.id,
                platform=platform,
                scheduled_for=scheduled_for,
                published_at=now_utc if res.status == "published" else None,
                url=res.url,
                status=res.status,
            )
            db.add(pub_record)
            persisted_publications.append(pub_record)
            if res.url:
                published_links.append(f"{platform.capitalize()}: {res.url}")

        db.commit()
        for p in persisted_publications:
            db.refresh(p)

        if self.notifier and published_links:
            links_text = "\n".join(f"• {link}" for link in published_links)
            msg = (
                f"🎉 <b>Vídeo Publicado com Sucesso!</b>\n\n"
                f"{links_text}"
            )
            self.notifier.client.send_message(text=msg)

        return persisted_publications

