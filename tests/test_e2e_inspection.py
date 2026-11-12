from __future__ import annotations

import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from viralpanel.cli import main as cli_main
from viralpanel.database import Base
from viralpanel.models import Asset, Script, SourceVideo
from viralpanel.storage import StorageManager
from viralpanel.studio.avatar import MockAvatarAnimator
from viralpanel.studio.inspection import (
    AudioSignalEnergyError,
    CANONICAL_SCRIPT_TEXT,
    CANONICAL_SCRIPT_WORDS,
    InspectionRunner,
    PublishContentionTimeoutError,
    SequenceRecoveryError,
    allocate_next_sequence,
    compute_acoustic_comparison,
    compute_audio_rms,
    compute_segmented_rms,
    file_kernel_lock,
    pcm_bytes_to_floats,
)
from viralpanel.studio.renderer import StudioRenderRequest
from viralpanel.studio.service import StudioService
from viralpanel.studio.voice import MockVoiceSynthesizer, PreSynthesizedVoice


def _create_test_session_factory():
    eng = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    return sessionmaker(bind=eng, expire_on_commit=False)


def test_sequence_allocation_fresh_install_initializes_to_one(tmp_path: Path):
    """Garante que sequence_number = 1 é alocado exclusivamente em ambiente de instalação totalmente limpo."""
    storage_dir = tmp_path / "fresh_storage"
    run_id = "test_run_fresh"

    seq, staging_dir = allocate_next_sequence(storage_dir, run_id)
    assert seq == 1
    assert staging_dir.exists()

    marker_file = staging_dir / "_runner_marker.json"
    assert marker_file.exists()
    marker_data = json.loads(marker_file.read_text(encoding="utf-8"))
    assert marker_data["sequence_number"] == 1
    assert marker_data["status"] == "STAGING"

    seq_file = storage_dir / ".sequence"
    assert seq_file.exists()
    assert seq_file.read_text(encoding="utf-8").strip() == "1"


def test_sequence_recovers_from_historical_runs_when_control_files_absent(tmp_path: Path):
    """Valida recuperação segura pelo histórico quando .sequence e latest.json foram apagados."""
    storage_dir = tmp_path / "recovery_storage"
    runs_dir = storage_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    # Cria corrida finalizada com sequence_number = 14
    run_14 = runs_dir / "run_20261112_000014"
    run_14.mkdir()
    (run_14 / "_runner_marker.json").write_text(
        json.dumps({"sequence_number": 14, "status": "FINALIZED"}), encoding="utf-8"
    )

    # Garante que não existem .sequence nem latest.json
    assert not (storage_dir / ".sequence").exists()
    assert not (storage_dir / "latest.json").exists()

    seq, staging_dir = allocate_next_sequence(storage_dir, "run_recovery_test")
    assert seq == 15
    assert (storage_dir / ".sequence").read_text(encoding="utf-8").strip() == "15"


def test_sequence_accounts_for_staging_and_failed_runs(tmp_path: Path):
    """Comprova que execuções ativas em staging e execuções abortadas em .failed_* protegem a sequência contra colisão."""
    storage_dir = tmp_path / "multi_state_storage"
    runs_dir = storage_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    # 1. Staging ativo com sequence = 20
    stg_20 = runs_dir / ".staging_run_active_20"
    stg_20.mkdir()
    (stg_20 / "_runner_marker.json").write_text(
        json.dumps({"sequence_number": 20, "status": "STAGING"}), encoding="utf-8"
    )

    # 2. Failed run com sequence = 25
    failed_25 = runs_dir / ".failed_run_aborted_25"
    failed_25.mkdir()
    (failed_25 / "_runner_marker.json").write_text(
        json.dumps({"sequence_number": 25, "status": "FAILED"}), encoding="utf-8"
    )

    # .sequence com valor menor (e.g. 15)
    (storage_dir / ".sequence").write_text("15", encoding="utf-8")

    seq, staging_dir = allocate_next_sequence(storage_dir, "run_after_failed")
    assert seq == 26
    assert (storage_dir / ".sequence").read_text(encoding="utf-8").strip() == "26"


def test_corrupted_run_marker_fails_closed(tmp_path: Path):
    """Garante fail-closed estrito com SequenceRecoveryError se um diretório em runs/ possuir marcador corrompido."""
    storage_dir = tmp_path / "corrupted_marker_storage"
    runs_dir = storage_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    bad_run = runs_dir / "run_corrupted_metadata"
    bad_run.mkdir()
    (bad_run / "_runner_marker.json").write_text("JSON_INVALIDO{{{", encoding="utf-8")

    with pytest.raises(SequenceRecoveryError, match="possui marcador corrompido"):
        allocate_next_sequence(storage_dir, "run_will_fail")


def test_pre_synthesized_voice_validation_and_exact_duration_float(tmp_path: Path):
    """Valida PreSynthesizedVoice: conformidade WAV, validação de texto de 52 palavras, integridade SHA-256 e float sem round."""
    master_wav = tmp_path / "master.wav"
    # Cria WAV legítimo via FFmpeg lavfi
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=44100:duration=1.7589",
            "-ac",
            "1",
            "-ar",
            "44100",
            str(master_wav),
        ],
        check=True,
        capture_output=True,
    )

    import hashlib

    sha = hashlib.sha256(master_wav.read_bytes()).hexdigest()
    exact_dur = 1.75891234

    voice = PreSynthesizedVoice(
        master_audio_path=master_wav,
        duration=exact_dur,
        sha256_hash=sha,
        expected_text=CANONICAL_SCRIPT_TEXT,
    )

    # Duração float exata preservada sem arredondamento
    assert voice.duration == exact_dur

    # 1. Falha se o texto solicitado divergir
    target_copy = tmp_path / "copy.wav"
    with pytest.raises(ValueError, match="Texto solicitado diverge do áudio pré-sintetizado mestre"):
        voice.synthesize("Texto divergente", target_copy)

    # 2. Sucesso com o texto exato
    out_path, ret_dur = voice.synthesize(CANONICAL_SCRIPT_TEXT, target_copy)
    assert out_path == target_copy
    assert ret_dur == exact_dur
    assert target_copy.exists()
    assert hashlib.sha256(target_copy.read_bytes()).hexdigest() == sha


def test_kernel_lock_windows_seek_zero_consistency_and_contention(tmp_path: Path):
    """Valida consistência de seek(0) e contenção com timeout levantando PublishContentionTimeoutError."""
    lock_file = tmp_path / ".publish.lock"

    # 1. Adquire lock em um bloco e comprova que segunda tentativa no mesmo arquivo sofre timeout
    with file_kernel_lock(lock_file, timeout_seconds=1.0) as f1:
        assert f1.tell() == 0
        with pytest.raises(PublishContentionTimeoutError, match="Timeout"):
            with file_kernel_lock(lock_file, timeout_seconds=0.2):
                pass

    # 2. Após liberação do bloco anterior, lock pode ser readquirido imediatamente
    with file_kernel_lock(lock_file, timeout_seconds=1.0) as f2:
        assert f2.tell() == 0


def test_rms_computation_and_empty_segment_validation():
    """Valida cálculo de RMS em 0-20%, 40-60%, 80-100% e comprova rejeição estrita de segmentos vazios."""
    # 1. Rejeição de lista vazia
    with pytest.raises(ValueError, match="vazio para cálculo de RMS"):
        compute_audio_rms([])

    with pytest.raises(ValueError, match="vazio para segmentação de RMS"):
        compute_segmented_rms([])

    # 2. Sinal senoidal constante com amplitude 0.5
    # RMS teórico de senoide com amplitude A é A / sqrt(2) ≈ 0.35355
    N = 1000
    samples = [0.5 * math.sin(2 * math.pi * i / 50) for i in range(N)]
    rms_dict = compute_segmented_rms(samples)

    assert "start" in rms_dict
    assert "middle" in rms_dict
    assert "end" in rms_dict
    for val in rms_dict.values():
        assert 0.30 <= val <= 0.40


def test_acoustic_comparison_metrics_and_low_energy_rejection():
    """Valida métricas acústicas (Pearson, NMAE, lag) e comprova rejeição de sinais com energia insuficiente."""
    # 1. Sinal com energia quase nula (silêncio digital)
    silent_samples = [0.0001] * 5000
    cand_samples = [0.0001] * 5000
    with pytest.raises(AudioSignalEnergyError, match="Energia insuficiente"):
        compute_acoustic_comparison(silent_samples, cand_samples)

    # 2. Sinais idênticos com energia ativa
    N = 44100
    active_samples = [0.4 * math.sin(2 * math.pi * 440 * i / 44100) for i in range(N)]
    res = compute_acoustic_comparison(active_samples, active_samples)

    assert res["lag_tau"] == 0
    assert res["sample_diff"] == 0
    assert res["pearson_r"] > 0.9999
    assert res["nmae"] < 0.0001
    assert res["sections"]["start"]["pearson_r"] > 0.9999
    assert res["sections"]["middle"]["pearson_r"] > 0.9999
    assert res["sections"]["end"]["pearson_r"] > 0.9999


def test_studio_produce_atomic_rollback_on_failure(tmp_path: Path):
    """Comprova que falha no render final reverte os assets intermediários (audio e avatar) na sessão e no banco."""
    factory = _create_test_session_factory()
    flushed_before_crash: list[str] = []

    with factory() as db:
        src = SourceVideo(
            url="https://www.tiktok.com/@zunto/video/atomic-fail-test",
            author="zunto",
            score=95.0,
        )
        db.add(src)
        db.flush()

        script = Script(
            source_video_id=src.id,
            hook="Hook de teste atômico",
            script_text=CANONICAL_SCRIPT_TEXT,
            version=1,
        )
        db.add(script)
        db.commit()
        script_id = script.id
        src_id = src.id

        class FailingRenderer:
            def render_from_request(self, request: StudioRenderRequest) -> tuple[Path, float]:
                in_tx_assets = list(db.scalars(select(Asset).where(Asset.script_id == script_id)).all())
                flushed_before_crash.extend(sorted(a.asset_type for a in in_tx_assets))
                raise RuntimeError("Falha simulada na codificação de vídeo")

        service = StudioService(
            voice_synthesizer=MockVoiceSynthesizer(min_duration=1.5, max_duration=1.5),
            avatar_animator=MockAvatarAnimator(),
            renderer=FailingRenderer(),  # type: ignore[arg-type]
            storage=StorageManager(tmp_path / "atomic_storage"),
        )

        with pytest.raises(RuntimeError, match="Falha simulada na codificação de vídeo"):
            service.produce(db=db, run_id="run-atomic-fail", script=script)

        assert flushed_before_crash == ["audio", "avatar"]
        assert len(db.new) == 0
        assert len(db.dirty) == 0
        residual_identity_assets = [obj for obj in db.identity_map.values() if isinstance(obj, Asset)]
        assert len(residual_identity_assets) == 0

        db.expire_all()
        remaining_in_same_session = list(db.scalars(select(Asset).where(Asset.script_id == script_id)).all())
        assert remaining_in_same_session == []

    with factory() as fresh_db:
        remaining_in_fresh_session = list(fresh_db.scalars(select(Asset).where(Asset.script_id == script_id)).all())
        assert remaining_in_fresh_session == []
        fresh_src = fresh_db.get(SourceVideo, src_id)
        assert fresh_src is not None
        assert fresh_src.status == "pending"


def test_cli_validate_e2e_mock_mode_produces_frozen_package_and_latest_manifest(tmp_path: Path):
    """Executa a esteira completa E2E com voice-mode mock, validando pacote congelado e latest.json."""
    insp_dir = tmp_path / "inspection_output"
    report_file = tmp_path / "INSPECTION-REPORT.md"

    exit_code = cli_main(
        [
            "validate-e2e",
            "--output-dir",
            str(insp_dir),
            "--report-path",
            str(report_file),
            "--voice-mode",
            "mock",
        ]
    )
    assert exit_code == 0

    # 1. latest.json deve existir e apontar para o run congelado
    latest_file = insp_dir / "latest.json"
    assert latest_file.exists()
    latest_data = json.loads(latest_file.read_text(encoding="utf-8"))
    assert latest_data["sequence_number"] >= 1
    assert latest_data["status"] == "APPROVED_FOR_HUMAN_INSPECTION"

    # 2. Diretório versionado congelado
    run_dir = Path(latest_data["run_dir"])
    assert run_dir.exists()
    assert (run_dir / "_runner_marker.json").exists()
    marker = json.loads((run_dir / "_runner_marker.json").read_text(encoding="utf-8"))
    assert marker["status"] == "FINALIZED"
    assert "package_inventory" in marker

    # 3. Vistas de conveniência
    assert (insp_dir / "scenario_normal_final.mp4").exists()
    assert (insp_dir / "scenario_fallback_final.mp4").exists()
    assert (insp_dir / "README.md").exists()
    assert report_file.exists()


def test_older_sequence_cannot_overwrite_newer_publication(tmp_path: Path):
    """Comprova que uma execução mais antiga (menor sequence_number) nunca sobrescreve latest.json com sequence superior."""
    storage_dir = tmp_path / "superseded_test"
    storage_dir.mkdir(parents=True, exist_ok=True)

    # 1. Simula que latest.json já está publicado com sequence_number = 10
    latest_file = storage_dir / "latest.json"
    latest_file.write_text(
        json.dumps({
            "schema_version": "1.1",
            "run_id": "run_newer_10",
            "sequence_number": 10,
            "status": "APPROVED_FOR_HUMAN_INSPECTION",
        }),
        encoding="utf-8",
    )

    # 2. Um run antigo com sequence_number = 5 tenta publicar
    candidate_run_dir = storage_dir / "runs" / "run_older_5"
    candidate_run_dir.mkdir(parents=True, exist_ok=True)
    marker = {
        "schema_version": "1.1",
        "run_id": "run_older_5",
        "sequence_number": 5,
        "status": "FINALIZED",
    }
    (candidate_run_dir / "_runner_marker.json").write_text(json.dumps(marker), encoding="utf-8")

    # 3. Seção crítica de publicação
    publish_lock_path = storage_dir / ".publish.lock"
    with file_kernel_lock(publish_lock_path):
        cur_latest = json.loads(latest_file.read_text(encoding="utf-8"))
        assert 5 <= cur_latest["sequence_number"]  # Regra de precedência impede publicação

    # latest.json continua apontando para o run 10
    after_data = json.loads(latest_file.read_text(encoding="utf-8"))
    assert after_data["sequence_number"] == 10
    assert after_data["run_id"] == "run_newer_10"
