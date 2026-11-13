import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from viralpanel.config import Settings
from viralpanel.database import Base
from viralpanel.discovery.base import ScrapedVideoMetadata
from viralpanel.discovery.service import DiscoveryService
from viralpanel.discovery.tiktok import (
    MockDiscoveryScraper,
    TikTokDiscoveryScraper,
    get_ytdlp_cmd as tiktok_get_ytdlp_cmd,
    normalize_tiktok_url,
)
from viralpanel.media.downloader import MediaDownloader, MockMediaDownloader, get_ytdlp_cmd as downloader_get_ytdlp_cmd
from viralpanel.media.transcriber import AudioTranscriber, MockTranscriber, TranscriptionResult
from viralpanel.models import Asset, PipelineRun, Script, SourceVideo
from viralpanel.scripting.gemini import (
    FallbackScriptWriter,
    GeneratedScriptSchema,
    MockGeminiScriptWriter,
    ScriptWriter,
)
from viralpanel.scripting.service import InsufficientSpeechError, ScriptingService
from viralpanel.storage import StorageManager


def _make_db_session():
    eng = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    return sessionmaker(bind=eng, expire_on_commit=False)


# =============================================================================
# 1. Testes de Executável do yt-dlp (Ausente vs Disponível)
# =============================================================================
def test_ytdlp_cmd_when_binary_in_path():
    with patch("shutil.which", return_value="C:\\tools\\yt-dlp.exe"):
        cmd = tiktok_get_ytdlp_cmd()
        assert cmd == ["yt-dlp"] or cmd == ["C:\\tools\\yt-dlp.exe"]
        cmd_dl = downloader_get_ytdlp_cmd()
        assert "yt-dlp" in cmd_dl[0]


def test_ytdlp_cmd_fallback_to_sys_executable_when_binary_not_in_path():
    with patch("shutil.which", return_value=None):
        cmd = tiktok_get_ytdlp_cmd()
        assert cmd == [sys.executable, "-m", "yt_dlp"]
        cmd_dl = downloader_get_ytdlp_cmd()
        assert cmd_dl == [sys.executable, "-m", "yt_dlp"]


def test_ytdlp_cmd_raises_or_returns_none_when_completely_absent():
    with patch("shutil.which", return_value=None), patch.dict("sys.modules", {"yt_dlp": None}):
        with patch("builtins.__import__", side_effect=ImportError("No module named yt_dlp")):
            assert tiktok_get_ytdlp_cmd() is None
            with pytest.raises(RuntimeError, match="yt-dlp não encontrado"):
                downloader_get_ytdlp_cmd()


# =============================================================================
# 2. Testes de Normalização e Deduplicação de URLs Equivalentes
# =============================================================================
def test_normalize_tiktok_url_variants():
    canon = "https://www.tiktok.com/@curiosidades/video/7123456789"

    # Variante com query params
    assert normalize_tiktok_url("https://www.tiktok.com/@curiosidades/video/7123456789?is_copy_url=1") == canon
    # Variante sem author no path
    assert normalize_tiktok_url("https://www.tiktok.com/video/7123456789", default_author="curiosidades") == canon
    # Variante mobile /v/
    assert normalize_tiktok_url("https://m.tiktok.com/v/7123456789.html", default_author="curiosidades") == canon
    # Variante apenas ID numérico
    assert normalize_tiktok_url("7123456789", default_author="curiosidades") == canon


def test_discovery_deduplicates_equivalent_urls():
    factory = _make_db_session()
    now = datetime(2026, 11, 13, 12, 0, tzinfo=timezone.utc)

    class CustomScraper:
        def discover_trending(self, **kwargs):
            return [
                ScrapedVideoMetadata(
                    url="https://www.tiktok.com/@vocesabia/video/88888888",
                    author="vocesabia",
                    views=50_000,
                    likes=5_000,
                    comments=300,
                    shares=200,
                    duration=60,
                    posted_at=now,
                ),
                ScrapedVideoMetadata(
                    url="https://www.tiktok.com/video/88888888?param=1",
                    author="vocesabia",
                    views=52_000,
                    likes=5_200,
                    comments=310,
                    shares=210,
                    duration=60,
                    posted_at=now,
                ),
            ]

    service = DiscoveryService(scraper=CustomScraper())
    with factory() as db:
        candidates = service.collect_and_rank(db=db, now=now)
        # Ambas as variantes normalizam para a mesma URL canônica
        assert len(candidates) == 1
        all_videos = db.scalars(select(SourceVideo)).all()
        assert len(all_videos) == 1
        assert all_videos[0].url == "https://www.tiktok.com/@vocesabia/video/88888888"


# =============================================================================
# 3. Teste de Rejeição de Candidatos com Score Zero ou Negativo
# =============================================================================
def test_select_best_candidate_ignores_zero_or_negative_scores():
    factory = _make_db_session()
    with factory() as db:
        # Candidato inválido com score 0.0 (ex: descartado por duração ou view insuficiente)
        zero_video = SourceVideo(
            url="https://www.tiktok.com/@user/video/0",
            author="user",
            score=0.0,
            status="pending",
        )
        db.add(zero_video)
        db.commit()

        service = DiscoveryService(scraper=MockDiscoveryScraper())
        best = service.select_best_candidate(db)
        assert best is None

        # Candidato válido com score positivo
        valid_video = SourceVideo(
            url="https://www.tiktok.com/@user/video/1",
            author="user",
            score=75.5,
            status="pending",
        )
        db.add(valid_video)
        db.commit()

        best = service.select_best_candidate(db)
        assert best is not None
        assert best.id == valid_video.id


# =============================================================================
# 4. Testes de Retentativa e Limpeza Prévia de Arquivos (Downloader)
# =============================================================================
def test_downloader_cleans_previous_files_on_retry(tmp_path):
    storage = StorageManager(tmp_path)
    dl = MockMediaDownloader(storage=storage)
    run_id = "run-test-clean"

    # 1. Simula primeiro download
    video1, audio1 = dl.fetch(run_id, "https://www.tiktok.com/@a/video/1")
    assert video1.exists() and audio1.exists()
    mtime_video1 = video1.stat().st_mtime_ns

    # Grava dado marcador
    video1.write_bytes(b"CANDIDATE_1_DATA")

    # 2. Simula download de segundo candidato para o mesmo run_id
    video2, audio2 = dl.fetch(run_id, "https://www.tiktok.com/@b/video/2")
    assert video2.exists() and audio2.exists()
    assert video2 == video1  # Mesmo arquivo canônico no run_id
    # Confirma que o arquivo foi limpo e regerado sem conter dados velhos
    assert video2.read_bytes() != b"CANDIDATE_1_DATA"


def test_scripting_service_cleans_files_on_insufficient_speech(tmp_path):
    storage = StorageManager(tmp_path)
    factory = _make_db_session()

    class SilentTranscriber(AudioTranscriber):
        def transcribe(self, audio_path):
            return TranscriptionResult(text="apenas tres palavras", language="pt", segments=[])

    dl = MockMediaDownloader(storage=storage)
    svc = ScriptingService(
        downloader=dl,
        transcriber=SilentTranscriber(),
        writer=MockGeminiScriptWriter(),
        min_speech_words=15,
    )

    with factory() as db:
        src = SourceVideo(url="https://www.tiktok.com/@c/video/silent", author="c", score=90.0, status="pending")
        db.add(src)
        db.commit()

        run_id = "run-silent-retry"
        with pytest.raises(InsufficientSpeechError):
            svc.process(db, run_id=run_id, source=src)

        # Confirma que os arquivos do candidato descartado foram limpos do disco
        target_video = dl.source_dir(run_id) / "source.mp4"
        target_audio = dl.source_dir(run_id) / "audio.wav"
        assert not target_video.exists()
        assert not target_audio.exists()
        assert src.status == "skipped_no_speech"


# =============================================================================
# 5. Testes de Eliminação de Mocks Silenciosos em Modo de Produção
# =============================================================================
def test_fallback_script_writer_raises_when_production_and_no_keys(monkeypatch):
    monkeypatch.setattr(
        "viralpanel.scripting.gemini.get_settings",
        lambda: Settings(
            gemini_api_key=None,
            groq_api_key=None,
            pipeline_mock_mode=False,
            _env_file=None,
        ),
    )
    with pytest.raises(RuntimeError, match="Nenhum provedor de IA real configurado.*PIPELINE_MOCK_MODE=false"):
        FallbackScriptWriter()


def test_fallback_script_writer_allows_mock_when_pipeline_mock_mode_is_true(monkeypatch):
    monkeypatch.setattr(
        "viralpanel.scripting.gemini.get_settings",
        lambda: Settings(
            gemini_api_key=None,
            groq_api_key=None,
            pipeline_mock_mode=True,
            _env_file=None,
        ),
    )
    writer = FallbackScriptWriter()
    assert len(writer.writers) == 1
    assert isinstance(writer.writers[0], MockGeminiScriptWriter)
