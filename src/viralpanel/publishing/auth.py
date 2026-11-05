from dataclasses import dataclass
from viralpanel.config import get_settings


@dataclass
class PlatformCredentials:
    tiktok_access_token: str | None = None
    instagram_access_token: str | None = None
    instagram_account_id: str | None = None
    youtube_client_secret: str | None = None
    youtube_refresh_token: str | None = None

    @classmethod
    def from_settings(cls) -> "PlatformCredentials":
        settings = get_settings()
        return cls(
            tiktok_access_token=settings.tiktok_access_token,
            instagram_access_token=settings.instagram_access_token,
            instagram_account_id=settings.instagram_account_id,
            youtube_client_secret=settings.youtube_client_secret,
            youtube_refresh_token=settings.youtube_refresh_token,
        )

    def is_platform_configured(self, platform: str) -> bool:
        plat = platform.lower()
        if plat == "tiktok":
            return bool(self.tiktok_access_token)
        elif plat in ("instagram", "reels"):
            return bool(self.instagram_access_token and self.instagram_account_id)
        elif plat in ("youtube", "shorts"):
            return bool(self.youtube_client_secret or self.youtube_refresh_token)
        return False

    def get_configured_platforms(self) -> list[str]:
        configured = []
        if self.is_platform_configured("tiktok"):
            configured.append("tiktok")
        if self.is_platform_configured("instagram"):
            configured.append("instagram")
        if self.is_platform_configured("youtube"):
            configured.append("youtube")
        return configured
