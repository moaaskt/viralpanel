from viralpanel.models import Script
from viralpanel.publishing.auth import PlatformCredentials
from viralpanel.publishing.metadata import MetadataGenerator


def test_platform_credentials_detection():
    creds = PlatformCredentials(
        tiktok_access_token="tok_tiktok_123",
        instagram_access_token="tok_insta_123",
        instagram_account_id="act_456",
        youtube_refresh_token="ref_yt_789",
    )
    assert creds.is_platform_configured("tiktok") is True
    assert creds.is_platform_configured("instagram") is True
    assert creds.is_platform_configured("youtube") is True
    assert set(creds.get_configured_platforms()) == {"tiktok", "instagram", "youtube"}

    unconfigured = PlatformCredentials()
    assert unconfigured.is_platform_configured("tiktok") is False
    assert unconfigured.is_platform_configured("instagram") is False
    assert unconfigured.is_platform_configured("youtube") is False
    assert unconfigured.get_configured_platforms() == []


def test_metadata_generator_for_all_platforms():
    generator = MetadataGenerator()
    script = Script(
        hook="Você não precisa de mais motivação, precisa de foco.",
        script_text="Você não precisa de mais motivação, precisa de foco. Cinco minutos por dia transformam qualquer rotina.",
    )

    # TikTok
    meta_tt = generator.generate(script, "tiktok")
    assert meta_tt.platform == "tiktok"
    assert "Você não precisa" in meta_tt.title
    assert "#fyp" in meta_tt.formatted_caption
    assert "desenvolvimentopessoal" in meta_tt.hashtags

    # Instagram
    meta_ig = generator.generate(script, "instagram")
    assert meta_ig.platform == "instagram"
    assert "#reels" in meta_ig.formatted_caption
    assert "Siga para mais" in meta_ig.formatted_caption

    # YouTube Shorts
    meta_yt = generator.generate(script, "youtube")
    assert meta_yt.platform == "youtube"
    assert meta_yt.title.endswith("#Shorts")
    assert len(meta_yt.title) <= 100
    assert "#Shorts" in meta_yt.formatted_caption

