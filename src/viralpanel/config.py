from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://viraluser:viralpass@localhost:5432/viralpanel"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    storage_dir: str = "./storage"
    timezone: str = "America/Sao_Paulo"
    log_level: str = "INFO"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.5-flash"
    gemini_fallback_model: str = "gemini-3.5-flash-lite"
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-120b"
    openrouter_api_key: str | None = None
    openrouter_model: str = "meta-llama/llama-3.3-70b-instruct:free"
    whisper_model: str = "small"
    tts_provider: str = "edge"
    edge_tts_voice: str = "pt-BR-AntonioNeural"
    edge_tts_rate: str = "+8%"
    speaker_wav_path: str | None = "assets/creator_voice.wav"
    avatar_image_path: str = "assets/creator_avatar.png"
    pipeline_mock_mode: bool = False
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    telegram_supervised_mode: bool = True
    tiktok_cookies_path: str | None = None
    tiktok_access_token: str | None = None
    instagram_access_token: str | None = None
    instagram_account_id: str | None = None
    youtube_client_secret: str | None = None
    youtube_refresh_token: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
