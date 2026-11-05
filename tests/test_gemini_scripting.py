import json

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from viralpanel.database import Base
from viralpanel.media.downloader import MockMediaDownloader
from viralpanel.media.transcriber import MockTranscriber
from viralpanel.models import Asset, Script, SourceVideo
from viralpanel.scripting.gemini import GeminiScriptWriter, GeneratedScriptSchema, MockGeminiScriptWriter
from viralpanel.scripting.service import ScriptingService
from viralpanel.storage import StorageManager


def test_schema_rejects_missing_blocks():
    with pytest.raises(ValidationError):
        GeneratedScriptSchema.model_validate({"hook": "Oi", "body": "", "cta": "", "estimated_duration_seconds": 5})


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
    assert "0–3s" in captured["prompt"] and "[000.00-003.00]" in captured["prompt"]


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
        assert db.scalars(select(Asset)).one().asset_type == "source_audio"
        assert len(db.scalars(select(Script)).all()) == 1

