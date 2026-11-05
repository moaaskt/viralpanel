import json
import urllib.request
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from viralpanel.config import get_settings


class BaseTelegramClient(ABC):
    @abstractmethod
    def send_message(
        self,
        text: str,
        chat_id: str | None = None,
        parse_mode: str = "HTML",
        reply_markup: dict | None = None,
    ) -> dict:
        raise NotImplementedError

    @abstractmethod
    def send_video(
        self,
        video_path: Path,
        caption: str = "",
        chat_id: str | None = None,
        parse_mode: str = "HTML",
        reply_markup: dict | None = None,
    ) -> dict:
        raise NotImplementedError

    @abstractmethod
    def answer_callback_query(self, callback_query_id: str, text: str = "") -> dict:
        raise NotImplementedError


class TelegramClient(BaseTelegramClient):
    """Cliente nativo sobre urllib.request para a Telegram Bot API oficial."""

    API_BASE = "https://api.telegram.org/bot{token}/{method}"

    def __init__(
        self,
        bot_token: str | None = None,
        default_chat_id: str | None = None,
        timeout: int = 60,
    ):
        settings = get_settings()
        self.bot_token = bot_token or settings.telegram_bot_token
        self.default_chat_id = default_chat_id or settings.telegram_chat_id
        if not self.bot_token:
            raise ValueError(
                "TELEGRAM_BOT_TOKEN ausente. Defina a variável no .env ou passe bot_token no construtor."
            )
        self.timeout = timeout

    def _resolve_chat_id(self, chat_id: str | None) -> str:
        resolved = chat_id or self.default_chat_id
        if not resolved:
            raise ValueError("TELEGRAM_CHAT_ID ausente.")
        return str(resolved)

    def _post_json(self, method: str, payload: dict) -> dict:
        url = self.API_BASE.format(token=self.bot_token, method=method)
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def send_message(
        self,
        text: str,
        chat_id: str | None = None,
        parse_mode: str = "HTML",
        reply_markup: dict | None = None,
    ) -> dict:
        payload: dict = {
            "chat_id": self._resolve_chat_id(chat_id),
            "text": text,
            "parse_mode": parse_mode,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        return self._post_json("sendMessage", payload)

    def send_video(
        self,
        video_path: Path,
        caption: str = "",
        chat_id: str | None = None,
        parse_mode: str = "HTML",
        reply_markup: dict | None = None,
    ) -> dict:
        resolved_chat = self._resolve_chat_id(chat_id)
        boundary = f"----ViralPanelBoundary{uuid.uuid4().hex}"
        body_parts: list[bytes] = []

        def _add_field(name: str, value: str) -> None:
            body_parts.append(
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                f"{value}\r\n".encode("utf-8")
            )

        _add_field("chat_id", resolved_chat)
        if caption:
            _add_field("caption", caption)
        if parse_mode:
            _add_field("parse_mode", parse_mode)
        if reply_markup is not None:
            _add_field("reply_markup", json.dumps(reply_markup))

        file_bytes = Path(video_path).read_bytes()
        body_parts.append(
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="video"; filename="{Path(video_path).name}"\r\n'
            f"Content-Type: video/mp4\r\n\r\n".encode("utf-8")
            + file_bytes
            + f"\r\n--{boundary}--\r\n".encode("utf-8")
        )

        url = self.API_BASE.format(token=self.bot_token, method="sendVideo")
        req = urllib.request.Request(
            url,
            data=b"".join(body_parts),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def answer_callback_query(self, callback_query_id: str, text: str = "") -> dict:
        return self._post_json(
            "answerCallbackQuery",
            {"callback_query_id": callback_query_id, "text": text},
        )


class MockTelegramClient(BaseTelegramClient):
    """Cliente em memória para testes unitários e execução offline."""

    def __init__(self, default_chat_id: str = "mock-chat-1"):
        self.default_chat_id = default_chat_id
        self.messages: list[dict] = []
        self.videos: list[dict] = []
        self.callbacks_answered: list[dict] = []

    def send_message(
        self,
        text: str,
        chat_id: str | None = None,
        parse_mode: str = "HTML",
        reply_markup: dict | None = None,
    ) -> dict:
        entry = {
            "message_id": len(self.messages) + 1,
            "chat_id": chat_id or self.default_chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "reply_markup": reply_markup,
        }
        self.messages.append(entry)
        return {"ok": True, "result": entry}

    def send_video(
        self,
        video_path: Path,
        caption: str = "",
        chat_id: str | None = None,
        parse_mode: str = "HTML",
        reply_markup: dict | None = None,
    ) -> dict:
        entry = {
            "message_id": len(self.videos) + 100,
            "chat_id": chat_id or self.default_chat_id,
            "video_path": str(video_path),
            "caption": caption,
            "parse_mode": parse_mode,
            "reply_markup": reply_markup,
        }
        self.videos.append(entry)
        return {"ok": True, "result": entry}

    def answer_callback_query(self, callback_query_id: str, text: str = "") -> dict:
        entry = {"callback_query_id": callback_query_id, "text": text}
        self.callbacks_answered.append(entry)
        return {"ok": True, "result": True}

