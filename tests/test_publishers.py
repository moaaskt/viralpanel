from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from viralpanel.publishing.base import MockPublisher
from viralpanel.publishing.instagram import InstagramPublisher
from viralpanel.publishing.metadata import MetadataGenerator
from viralpanel.publishing.tiktok import TikTokPublisher
from viralpanel.publishing.youtube import YouTubePublisher


def test_mock_publisher_records_and_formats_url(tmp_path):
    dummy_video = tmp_path / "video.mp4"
    dummy_video.write_bytes(b"TESTDATA")

    meta = MetadataGenerator().generate("Foco diário", "tiktok")
    mock_tt = MockPublisher("tiktok")
    res = mock_tt.publish(dummy_video, meta)

    assert res.success is True
    assert res.platform == "tiktok"
    assert "tiktok.com" in res.url
    assert res.status == "published"
    assert len(mock_tt.published_items) == 1

    # Test scheduled publish
    future = datetime(2026, 12, 1, 10, 0, tzinfo=timezone.utc)
    res_sched = mock_tt.publish(dummy_video, meta, scheduled_for=future)
    assert res_sched.status == "scheduled"
    assert res_sched.scheduled_for == future


def test_tiktok_publisher_handles_missing_token(tmp_path):
    dummy_video = tmp_path / "video.mp4"
    dummy_video.write_bytes(b"TESTDATA")
    meta = MetadataGenerator().generate("Texto", "tiktok")

    pub = TikTokPublisher(access_token=None)
    res = pub.publish(dummy_video, meta)
    assert res.success is False
    assert "não configurado" in res.error_message


def _create_mock_response(json_bytes: bytes):
    mock = MagicMock()
    mock.__enter__.return_value = mock
    mock.read.return_value = json_bytes
    return mock


def test_tiktok_publisher_success_call(tmp_path):
    dummy_video = tmp_path / "video.mp4"
    dummy_video.write_bytes(b"TESTDATA")
    meta = MetadataGenerator().generate("Texto", "tiktok")

    pub = TikTokPublisher(access_token="fake_token")
    mock_resp = _create_mock_response(b'{"data": {"publish_id": "tt_12345"}}')

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = pub.publish(dummy_video, meta)
        assert res.success is True
        assert res.publication_id == "tt_12345"
        assert "tt_12345" in res.url


def test_instagram_publisher_success_call(tmp_path):
    dummy_video = tmp_path / "video.mp4"
    dummy_video.write_bytes(b"TESTDATA")
    meta = MetadataGenerator().generate("Texto", "instagram")

    pub = InstagramPublisher(access_token="fake_token", account_id="act_123")
    mock_resp1 = _create_mock_response(b'{"id": "container_abc"}')
    mock_resp2 = _create_mock_response(b'{"id": "reel_xyz"}')

    with patch("urllib.request.urlopen", side_effect=[mock_resp1, mock_resp2]):
        res = pub.publish(dummy_video, meta)
        assert res.success is True
        assert res.publication_id == "reel_xyz"
        assert "reel_xyz" in res.url


def test_youtube_publisher_success_call(tmp_path):
    dummy_video = tmp_path / "video.mp4"
    dummy_video.write_bytes(b"TESTDATA")
    meta = MetadataGenerator().generate("Texto", "youtube")

    pub = YouTubePublisher(access_token="fake_token")
    mock_resp = _create_mock_response(b'{"id": "yt_short_999"}')

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = pub.publish(dummy_video, meta)
        assert res.success is True
        assert res.publication_id == "yt_short_999"
        assert "shorts/yt_short_999" in res.url

