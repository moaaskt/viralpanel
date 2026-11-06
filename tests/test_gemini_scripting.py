import json

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from viralpanel.database import Base
from viralpanel.media.downloader import MockMediaDownloader
from viralpanel.media.transcriber import AudioTranscriber, MockTranscriber, TranscriptionResult
from viralpanel.models import Asset, Script, SourceVideo
from viralpanel.scripting.gemini import (
    FallbackScriptWriter,
    GeminiScriptWriter,
    GeneratedScriptSchema,
    GroqScriptWriter,
    MockGeminiScriptWriter,
    ScriptWriter,
)
from viralpanel.scripting.service import InsufficientSpeechError, ScriptingService
from viralpanel.storage import StorageManager


def test_gemini_writer_loads_api_key_from_settings(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "env-secret-key")
    from viralpanel.config import get_settings
    get_settings.cache_clear()
    writer = GeminiScriptWriter()
    assert writer.api_key == "env-secret-key"
    get_settings.cache_clear()


def test_gemini_writer_raises_when_no_key_available(monkeypatch):
    from viralpanel.config import Settings
    monkeypatch.setattr("viralpanel.scripting.gemini.get_settings", lambda: Settings(gemini_api_key=None, _env_file=None))
    with pytest.raises(ValueError, match="GEMINI_API_KEY ausente"):
        GeminiScriptWriter(api_key=None)




def test_gemini_writer_parses_structured_json(monkeypatch):
    writer = GeminiScriptWriter(api_key="fake")
    payload = {
        "theme": "foco",
        "hook": "Seu celular está roubando sua vida.",
        "body": "Cada notificação quebra seu foco por minutos. " * 3,
        "cta": "Me segue para mais.",
        "estimated_duration_seconds": 30,
    }
    captured = {}

    def fake_call(prompt):
        captured["prompt"] = prompt
        return json.dumps(payload)

    monkeypatch.setattr(writer, "_call", fake_call)
    out = writer.generate(MockTranscriber().transcribe(None))
    assert out.hook == payload["hook"]
    assert ("[000.00-003.00]" in captured["prompt"]) and ("0–3" in captured["prompt"] or "0-3" in captured["prompt"])


def test_scripting_service_persists_script_and_asset(tmp_path):
    eng = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    factory = sessionmaker(bind=eng, expire_on_commit=False)
    svc = ScriptingService(
        MockMediaDownloader(storage=StorageManager(tmp_path)), MockTranscriber(), MockGeminiScriptWriter()
    )
    with factory() as db:
        src = SourceVideo(url="https://www.tiktok.com/@a/video/1", author="a", score=10)
        db.add(src)
        db.commit()
        script = svc.process(db, run_id="r1", source=src)
        assert script.version == 1
        assert script.hook and "Salva" in script.script_text
        assert src.status == "scripted"
        assets = list(db.scalars(select(Asset)).all())
        assert len(assets) == 2
        asset_types = {a.asset_type for a in assets}
        assert "source_video" in asset_types
        assert "source_audio" in asset_types
        assert len(db.scalars(select(Script)).all()) == 1


def test_groq_writer_raises_when_no_key_available(monkeypatch):
    from viralpanel.config import Settings
    monkeypatch.setattr("viralpanel.scripting.gemini.get_settings", lambda: Settings(groq_api_key=None, _env_file=None))
    with pytest.raises(ValueError, match="GROQ_API_KEY ausente"):
        GroqScriptWriter(api_key=None)


def test_groq_writer_parses_structured_json(monkeypatch):
    writer = GroqScriptWriter(api_key="fake-groq-key")
    payload = {
        "theme": "foco e dopamina",
        "hook": "Seu cérebro está sendo hackeado.",
        "body": "A dopamina barata destrói sua disciplina diária.",
        "cta": "Me segue para blindar sua mente.",
        "estimated_duration_seconds": 35.0,
    }

    def fake_call(prompt):
        return json.dumps(payload)

    monkeypatch.setattr(writer, "_call", fake_call)
    out = writer.generate(TranscriptionResult(text="foco e disciplina", language="pt", segments=[]))
    assert out.theme == payload["theme"]
    assert out.hook == payload["hook"]
    assert out.estimated_duration_seconds == 35.0


def test_fallback_script_writer_advances_on_error():
    class FailingWriter(ScriptWriter):
        def generate(self, tr, fallback_context=""):
            raise RuntimeError("Primary API 503 Unavailable")

    class SuccessfulWriter(ScriptWriter):
        def generate(self, tr, fallback_context=""):
            return GeneratedScriptSchema(
                theme="Fallback Success",
                hook="Funcionou pelo fallback!",
                body="Conteúdo gerado com sucesso.",
                cta="Siga o canal.",
                estimated_duration_seconds=30.0,
            )

    writer = FallbackScriptWriter(writers=[FailingWriter(), SuccessfulWriter()])
    res = writer.generate(TranscriptionResult(text="teste", language="pt", segments=[]))
    assert res.theme == "Fallback Success"
    assert res.hook == "Funcionou pelo fallback!"


def test_fallback_script_writer_raises_when_all_fail():
    class FailingWriter(ScriptWriter):
        def generate(self, tr, fallback_context=""):
            raise RuntimeError("API Unavailable")

    writer = FallbackScriptWriter(writers=[FailingWriter(), FailingWriter()])
    with pytest.raises(RuntimeError, match="Todos os provedores da cadeia de IA falharam"):
        writer.generate(TranscriptionResult(text="teste", language="pt", segments=[]))


def test_scripting_service_rejects_insufficient_speech(tmp_path):
    class ShortSpeechTranscriber(AudioTranscriber):
        def transcribe(self, audio_path):
            return TranscriptionResult(text="apenas tres palavras", language="pt", segments=[])

    eng = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    factory = sessionmaker(bind=eng, expire_on_commit=False)
    svc = ScriptingService(
        MockMediaDownloader(storage=StorageManager(tmp_path)),
        ShortSpeechTranscriber(),
        MockGeminiScriptWriter(),
        min_speech_words=15,
    )
    with factory() as db:
        src = SourceVideo(url="https://www.tiktok.com/@a/video/music_only", author="a", score=50)
        db.add(src)
        db.commit()
        with pytest.raises(InsufficientSpeechError, match="rejeitado"):
            svc.process(db, run_id="r_skip", source=src)
        db.refresh(src)
        assert src.status == "skipped_no_speech"



