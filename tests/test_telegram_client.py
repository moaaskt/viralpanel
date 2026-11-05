import pytest

from viralpanel.config import Settings
from viralpanel.telegram.client import MockTelegramClient, TelegramClient
from viralpanel.telegram.notifier import TelegramNotifier


def test_telegram_client_requires_token(monkeypatch):
    monkeypatch.setattr(
        "viralpanel.telegram.client.get_settings",
        lambda: Settings(telegram_bot_token=None, _env_file=None),
    )
    with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN ausente"):
        TelegramClient(bot_token=None)


def test_telegram_notifier_formats_pipeline_events():
    mock_client = MockTelegramClient(default_chat_id="chat-99")
    notifier = TelegramNotifier(client=mock_client)

    notifier.notify_pipeline_started("run-1", "2026-11-05")
    notifier.notify_stage_completed("run-1", "discovery", {"collected": 30, "selected_score": 142.5})
    notifier.notify_error("run-1", "scripting", "Timeout na API")
    notifier.notify_pipeline_success(
        "run-1",
        {"selected_video_url": "https://tiktok.com/@a/video/1", "selected_video_score": 142.5, "approval_status": "approved"},
    )

    assert len(mock_client.messages) == 4
    assert "Pipeline Iniciado" in mock_client.messages[0]["text"]
    assert "DISCOVERY" in mock_client.messages[1]["text"]
    assert "Timeout na API" in mock_client.messages[2]["text"]
    assert "Pipeline Finalizado" in mock_client.messages[3]["text"]

