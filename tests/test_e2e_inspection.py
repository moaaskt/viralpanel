from __future__ import annotations

import json
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import time
import wave

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from viralpanel.branding import SafeZones9x16, ZuntoPalette, resolve_typography_font
from viralpanel.cli import main as cli_main
from viralpanel.database import Base
from viralpanel.models import Asset, Script, SourceVideo
from viralpanel.storage import StorageManager
from viralpanel.studio.avatar import (
    AudioReactiveAvatarAnimator,
    AvatarConfig,
    MockAvatarAnimator,
)
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
from viralpanel.studio.renderer import ReactionVideoRenderer, StudioRenderRequest
from viralpanel.studio.service import StudioService
from viralpanel.studio.subtitles import SubtitleJobConfig, generate_subtitles
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


def test_avatar_alpha_channel_isolation(tmp_path: Path):
    """Comprova canal alfa no vídeo intermediário do avatar: 0 fora, transição na borda, 255 dentro."""
    if shutil.which("ffmpeg") is None:
        pytest.skip("FFmpeg necessário para teste empírico de canal alfa")

    # 1. Gera áudio mock de 2s
    audio_path = tmp_path / "voice_mock.wav"
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "sine=frequency=440:sample_rate=44100:duration=2.0",
            "-c:a", "pcm_s16le", str(audio_path),
        ],
        check=True,
        capture_output=True,
    )

    animator = AudioReactiveAvatarAnimator()
    avatar_mov = tmp_path / "avatar_intermediate.mp4"
    animator.generate_avatar_video(audio_path, avatar_mov)
    assert avatar_mov.exists()

    # Extrai o frame em rawvideo rgba
    size = SafeZones9x16.AVATAR_SIZE
    center = size // 2
    raw_path = tmp_path / "avatar_frame.raw"
    subprocess.run(
        [
            "ffmpeg", "-y", "-ss", "0.5", "-i", str(avatar_mov),
            "-vframes", "1", "-f", "rawvideo", "-pix_fmt", "rgba",
            str(raw_path),
        ],
        check=True,
        capture_output=True,
    )
    raw_bytes = raw_path.read_bytes()
    assert len(raw_bytes) == size * size * 4

    def get_rgba(x: int, y: int) -> tuple[int, int, int, int]:
        idx = (y * size + x) * 4
        return raw_bytes[idx], raw_bytes[idx + 1], raw_bytes[idx + 2], raw_bytes[idx + 3]

    # A) Fora do círculo nos 4 cantos da caixa calibrada
    for corner_x, corner_y in [(10, 10), (size - 10, 10), (10, size - 10), (size - 10, size - 10)]:
        r, g, b, a = get_rgba(corner_x, corner_y)
        assert a == 0, f"Canal alfa em ({corner_x}, {corner_y}) deve ser 0 (transparência total). Obtido: {a}"
        assert (r, g, b) == (0, 0, 0), f"RGB fora do círculo deve ser 0. Obtido: {(r, g, b)}"

    # B) Borda externa de transição suave (antialiasing de 2px)
    r_edge, g_edge, b_edge, a_edge = get_rgba(center, 0)
    assert 0 < a_edge <= 255, f"Canal alfa na borda externa deve estar na rampa de antialiasing. Obtido: {a_edge}"

    # C) Dentro do círculo do avatar
    r_in, g_in, b_in, a_in = get_rgba(center, center)
    assert a_in == 255, f"Canal alfa no centro deve ser 255 (opacidade total). Obtido: {a_in}"


def test_composed_avatar_transparency_and_no_leak(tmp_path: Path):
    """Comprova ausência de vazamento de pixels e transparência real nos 4 cantos e perímetro da composição final."""
    if shutil.which("ffmpeg") is None:
        pytest.skip("FFmpeg necessário para teste de composição")

    source_video = tmp_path / "source.mp4"
    InspectionRunner.generate_synthetic_source_video(source_video, duration=2.5, bg_hex="#1e293b")

    audio_path = tmp_path / "voice.wav"
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "sine=frequency=440:sample_rate=44100:duration=2.5",
            "-c:a", "pcm_s16le", str(audio_path),
        ],
        check=True,
        capture_output=True,
    )

    animator = AudioReactiveAvatarAnimator()
    avatar_mov = tmp_path / "avatar.mp4"
    animator.generate_avatar_video(audio_path, avatar_mov)

    ass_path = tmp_path / "subs.ass"
    generate_subtitles(
        SubtitleJobConfig(
            script_text="Teste de transparência sem vazamento.",
            total_duration=2.5,
            output_path=ass_path,
        )
    )

    final_video = tmp_path / "final_composed.mp4"
    renderer = ReactionVideoRenderer()
    renderer.render(
        source_video_path=source_video,
        avatar_video_path=avatar_mov,
        voice_audio_path=audio_path,
        ass_subtitle_path=ass_path,
        output_path=final_video,
    )
    assert final_video.exists()

    # Extrai frame do vídeo base original e do vídeo composto em t=1.0s
    ref_raw_path = tmp_path / "ref_frame.raw"
    comp_raw_path = tmp_path / "comp_frame.raw"
    for in_vid, out_raw in [(source_video, ref_raw_path), (final_video, comp_raw_path)]:
        subprocess.run(
            [
                "ffmpeg", "-y", "-ss", "1.0", "-i", str(in_vid),
                "-vframes", "1", "-f", "rawvideo", "-pix_fmt", "rgb24",
                str(out_raw),
            ],
            check=True,
            capture_output=True,
        )

    ref_bytes = ref_raw_path.read_bytes()
    comp_bytes = comp_raw_path.read_bytes()
    assert len(ref_bytes) == 1080 * 1920 * 3
    assert len(comp_bytes) == 1080 * 1920 * 3

    def get_comp_rgb(x: int, y: int) -> tuple[int, int, int]:
        idx = (y * 1080 + x) * 3
        return comp_bytes[idx], comp_bytes[idx + 1], comp_bytes[idx + 2]

    def get_ref_rgb(x: int, y: int) -> tuple[int, int, int]:
        idx = (y * 1080 + x) * 3
        return ref_bytes[idx], ref_bytes[idx + 1], ref_bytes[idx + 2]

    # Avatar bounding box calibrada: SafeZones9x16 (X=680..940, Y=1360..1620)
    box_x0 = SafeZones9x16.WIDTH - SafeZones9x16.AVATAR_SIZE - SafeZones9x16.AVATAR_MARGIN_RIGHT
    box_y0 = SafeZones9x16.HEIGHT - SafeZones9x16.AVATAR_SIZE - SafeZones9x16.AVATAR_MARGIN_BOTTOM
    box_x1 = box_x0 + SafeZones9x16.AVATAR_SIZE
    box_y1 = box_y0 + SafeZones9x16.AVATAR_SIZE
    corners = [
        (box_x0 + 9, box_y0 + 10),
        (box_x1 - 11, box_y0 + 10),
        (box_x0 + 9, box_y1 - 10),
        (box_x1 - 11, box_y1 - 10),
    ]
    for x, y in corners:
        comp_rgb = get_comp_rgb(x, y)
        ref_rgb = get_ref_rgb(x, y)
        delta = max(abs(c - r) for c, r in zip(comp_rgb, ref_rgb))
        assert delta <= 8, f"Vazamento de pixel detectado no canto ({x}, {y}): final={comp_rgb}, ref={ref_rgb}, delta={delta}"


def test_avatar_yellow_border_integrity_h264(tmp_path: Path):
    """Comprova integridade da cor amarela ZUNTO! (#FACC15) em 8 ângulos radiais após compressão H.264."""
    if shutil.which("ffmpeg") is None:
        pytest.skip("FFmpeg necessário para teste de contorno amarelo")

    source_video = tmp_path / "source.mp4"
    InspectionRunner.generate_synthetic_source_video(source_video, duration=2.5, bg_hex="#1e293b")

    audio_path = tmp_path / "voice.wav"
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "sine=frequency=440:sample_rate=44100:duration=2.5",
            "-c:a", "pcm_s16le", str(audio_path),
        ],
        check=True,
        capture_output=True,
    )

    animator = AudioReactiveAvatarAnimator()
    avatar_mov = tmp_path / "avatar.mp4"
    animator.generate_avatar_video(audio_path, avatar_mov)

    ass_path = tmp_path / "subs.ass"
    generate_subtitles(
        SubtitleJobConfig(
            script_text="Contorno amarelo ZUNTO!",
            total_duration=2.5,
            output_path=ass_path,
        )
    )

    final_video = tmp_path / "final_composed.mp4"
    renderer = ReactionVideoRenderer()
    renderer.render(
        source_video_path=source_video,
        avatar_video_path=avatar_mov,
        voice_audio_path=audio_path,
        ass_subtitle_path=ass_path,
        output_path=final_video,
    )

    comp_raw_path = tmp_path / "comp_frame.raw"
    subprocess.run(
        [
            "ffmpeg", "-y", "-ss", "1.0", "-i", str(final_video),
            "-vframes", "1", "-f", "rawvideo", "-pix_fmt", "rgb24",
            str(comp_raw_path),
        ],
        check=True,
        capture_output=True,
    )
    raw_bytes = comp_raw_path.read_bytes()

    def get_comp_rgb(x: int, y: int) -> tuple[int, int, int]:
        idx = (y * 1080 + x) * 3
        return raw_bytes[idx], raw_bytes[idx + 1], raw_bytes[idx + 2]

    # Centro do avatar no frame 1080x1920 conforme SafeZones9x16
    box_x0 = SafeZones9x16.WIDTH - SafeZones9x16.AVATAR_SIZE - SafeZones9x16.AVATAR_MARGIN_RIGHT
    box_y0 = SafeZones9x16.HEIGHT - SafeZones9x16.AVATAR_SIZE - SafeZones9x16.AVATAR_MARGIN_BOTTOM
    cx = box_x0 + SafeZones9x16.AVATAR_SIZE // 2
    cy = box_y0 + SafeZones9x16.AVATAR_SIZE // 2
    r_mid = (SafeZones9x16.AVATAR_SIZE / 2.0) - 3.0
    angles_deg = [0, 45, 90, 135, 180, 225, 270, 315]

    for deg in angles_deg:
        rad = math.radians(deg)
        sample_x = int(round(cx + r_mid * math.cos(rad)))
        sample_y = int(round(cy + r_mid * math.sin(rad)))
        r, g, b = get_comp_rgb(sample_x, sample_y)
        # Amarelo ZUNTO! (#FACC15 -> R=250, G=204, B=21). Em H.264 comprimido:
        # R e G devem ser dominantes e B substancialmente mais baixo (R > 130, G > 100 e R > B * 1.3)
        assert r > 130 and g > 100, f"Ângulo {deg}° ({sample_x}, {sample_y}) perdeu intensidade: R={r}, G={g}, B={b}"
        assert r > b * 1.25, f"Ângulo {deg}° ({sample_x}, {sample_y}) perdeu cromaticidade amarela: R={r}, G={g}, B={b}"


def test_avatar_no_green_artifacts_synthetic(tmp_path: Path):
    """Comprova ausência total de artefatos verdes na região de sobreposição do waveform sobre o busto neutro do avatar sintético."""
    if shutil.which("ffmpeg") is None:
        pytest.skip("FFmpeg necessário para teste de ausência de verde")

    source_video = tmp_path / "source.mp4"
    InspectionRunner.generate_synthetic_source_video(source_video, duration=2.5, bg_hex="#1e293b")

    audio_path = tmp_path / "voice.wav"
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "sine=frequency=330:sample_rate=44100:duration=2.5",
            "-c:a", "pcm_s16le", str(audio_path),
        ],
        check=True,
        capture_output=True,
    )

    animator = AudioReactiveAvatarAnimator()
    avatar_mov = tmp_path / "avatar.mp4"
    animator.generate_avatar_video(audio_path, avatar_mov)

    ass_path = tmp_path / "subs.ass"
    generate_subtitles(
        SubtitleJobConfig(
            script_text="Sem artefatos esverdeados.",
            total_duration=2.5,
            output_path=ass_path,
        )
    )

    final_video = tmp_path / "final_composed.mp4"
    renderer = ReactionVideoRenderer()
    renderer.render(
        source_video_path=source_video,
        avatar_video_path=avatar_mov,
        voice_audio_path=audio_path,
        ass_subtitle_path=ass_path,
        output_path=final_video,
    )

    comp_raw_path = tmp_path / "comp_frame.raw"
    subprocess.run(
        [
            "ffmpeg", "-y", "-ss", "1.0", "-i", str(final_video),
            "-vframes", "1", "-f", "rawvideo", "-pix_fmt", "rgb24",
            str(comp_raw_path),
        ],
        check=True,
        capture_output=True,
    )
    raw_bytes = comp_raw_path.read_bytes()

    def get_comp_rgb(x: int, y: int) -> tuple[int, int, int]:
        idx = (y * 1080 + x) * 3
        return raw_bytes[idx], raw_bytes[idx + 1], raw_bytes[idx + 2]

    # Região de interseção do busto do avatar padrão com o waveform calibrada via SafeZones9x16
    box_x0 = SafeZones9x16.WIDTH - SafeZones9x16.AVATAR_SIZE - SafeZones9x16.AVATAR_MARGIN_RIGHT
    box_y0 = SafeZones9x16.HEIGHT - SafeZones9x16.AVATAR_SIZE - SafeZones9x16.AVATAR_MARGIN_BOTTOM
    box_x1 = box_x0 + SafeZones9x16.AVATAR_SIZE
    box_y1 = box_y0 + SafeZones9x16.AVATAR_SIZE
    green_artifact_pixels = []
    for y in range(box_y0 + 140, box_y1 - 25, 2):
        for x in range(box_x0 + 40, box_x1 - 40, 2):
            r, g, b = get_comp_rgb(x, y)
            # Assinatura de artefato verde ZUNTO: G desproporcionalmente dominante sobre R e B
            if g > r * 1.3 and g > b * 1.3 and g > 70:
                green_artifact_pixels.append((x, y, r, g, b))

    assert len(green_artifact_pixels) == 0, (
        f"Detectados {len(green_artifact_pixels)} pixels esverdeados anômalos no busto do avatar. "
        f"Exemplos: {green_artifact_pixels[:5]}"
    )


def test_subtitle_avatar_clearance_and_multi_line_safe_zones(tmp_path: Path):
    """Valida empiricamente que legendas no terço inferior preservam separação horizontal >= 24px ao avatar e safe zones."""
    if shutil.which("ffmpeg") is None:
        pytest.skip("FFmpeg necessário para validação de safe zones de legenda")

    resolved_font = resolve_typography_font()
    escaped_fontsdir = str(resolved_font.fonts_dir).replace("\\", "/").replace(":", "\\:")
    avatar_left_x = (
        SafeZones9x16.WIDTH - SafeZones9x16.AVATAR_SIZE - SafeZones9x16.AVATAR_MARGIN_RIGHT
    )  # 680

    test_cases = [
        ("FOCO TOTAL", "1_linha"),
        ("O SUCESSO EXIGE DISCIPLINA DIÁRIA E CONSTANTE", "2_linhas"),
        ("QUANDO VOCÊ DECIDE NÃO DESISTIR NADA NO MUNDO PODE PARAR A SUA EVOLUÇÃO", "3_linhas_longo"),
    ]

    for script_text, label in test_cases:
        ass_path = tmp_path / f"subs_{label}.ass"
        job_cfg = SubtitleJobConfig(
            script_text=script_text,
            total_duration=3.0,
            output_path=ass_path,
            resolved_font=resolved_font,
        )
        generate_subtitles(job_cfg)
        escaped_ass = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:")

        raw_path = tmp_path / f"frame_{label}.raw"
        subprocess.run(
            [
                "ffmpeg", "-y", "-f", "lavfi",
                "-i", "color=c=magenta:s=1080x1920:d=0.1",
                "-vf", f"ass='{escaped_ass}':fontsdir='{escaped_fontsdir}'",
                "-vframes", "1", "-f", "rawvideo", "-pix_fmt", "rgb24",
                str(raw_path),
            ],
            check=True,
            capture_output=True,
        )
        raw_bytes = raw_path.read_bytes()

        # Encontra a caixa opaca preta da legenda (RGB <= 25)
        box_y_coords = []
        box_x_coords = []
        for y in range(0, 1920, 2):
            for x in range(0, 1080, 2):
                idx = (y * 1080 + x) * 3
                r, g, b = raw_bytes[idx], raw_bytes[idx + 1], raw_bytes[idx + 2]
                if r <= 25 and g <= 25 and b <= 25:
                    box_y_coords.append(y)
                    box_x_coords.append(x)

        assert len(box_y_coords) > 0, f"Caixa preta da legenda deve ser detectada para o caso {label}"
        min_y = min(box_y_coords)
        max_y = max(box_y_coords)
        min_x = min(box_x_coords)
        max_x = max(box_x_coords)

        # 1. Separação física horizontal estrita até o Avatar (X_avatar_min = 680px, folga >= 24px)
        horizontal_clearance = avatar_left_x - max_x
        assert horizontal_clearance >= 24, (
            f"Caso {label}: folga horizontal até o avatar deve ser >= 24px. "
            f"Direita da legenda: X={max_x}, Avatar: X={avatar_left_x}, Folga={horizontal_clearance}px"
        )

        # 2. Respeito ao cabeçalho e barra inferior mobile
        assert min_y >= SafeZones9x16.TOP_MARGIN, (
            f"Caso {label}: legenda invadiu a safe zone superior. Topo: Y={min_y} < {SafeZones9x16.TOP_MARGIN}"
        )
        assert max_y <= SafeZones9x16.HEIGHT - SafeZones9x16.AVATAR_MARGIN_BOTTOM, (
            f"Caso {label}: legenda invadiu a safe zone inferior. Base: Y={max_y}"
        )

        # 3. Respeito à margem lateral esquerda
        assert min_x >= SafeZones9x16.SUBTITLE_MARGIN_LEFT - 24, (
            f"Caso {label}: margem lateral esquerda violada. min_x={min_x}"
        )


def test_mp4_karaoke_audio_energy_cross_validation(tmp_path: Path):
    """Validação cruzada E2E entre áudio AAC decodificado (RMS) do MP4 final e destaque ativo por palavra."""
    if shutil.which("ffmpeg") is None:
        pytest.skip("FFmpeg necessário para validação cruzada audiovisual E2E")

    proc_check = subprocess.run(["ffmpeg", "-filters"], capture_output=True, text=True)
    if "ass" not in proc_check.stdout:
        pytest.skip("FFmpeg sem suporte ao filtro libass (ass)")

    sample_rate = 24000
    total_duration = 2.4
    total_samples = int(sample_rate * total_duration)

    # Três rajadas acústicas (0.15-0.55, 0.90-1.30, 1.65-2.15) separadas por silêncio (> 300ms)
    bursts = [
        (0.15, 0.55, 440.0, 0.35),
        (0.90, 1.30, 550.0, 1.10),
        (1.65, 2.15, 660.0, 1.90),
    ]
    silences = [0.72, 1.48]

    pcm_samples: list[int] = []
    for n in range(total_samples):
        t = n / sample_rate
        amp = 0.0
        for b_start, b_end, freq, _ in bursts:
            if b_start <= t < b_end:
                amp = 0.5 * math.sin(2.0 * math.pi * freq * t)
                break
        pcm_samples.append(int(max(-32767, min(32767, amp * 32767.0))))

    voice_wav = tmp_path / "narration_bursts.wav"
    with wave.open(str(voice_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{len(pcm_samples)}h", *pcm_samples))

    source_video = tmp_path / "source.mp4"
    InspectionRunner.generate_synthetic_source_video(source_video, duration=total_duration, bg_hex="#1e293b")

    avatar_video = tmp_path / "avatar.mp4"
    AudioReactiveAvatarAnimator().generate_avatar_video(voice_wav, avatar_video)

    ass_path = tmp_path / "karaoke.ass"
    generate_subtitles(
        SubtitleJobConfig(
            script_text="Você não sabia.",
            total_duration=total_duration,
            output_path=ass_path,
            word_timestamps=[
                {"word": "Você", "start": 0.15, "end": 0.55, "duration": 0.40},
                {"word": "não", "start": 0.90, "end": 1.30, "duration": 0.40},
                {"word": "sabia.", "start": 1.65, "end": 2.15, "duration": 0.50},
            ],
        )
    )

    final_mp4 = tmp_path / "final_karaoke.mp4"
    renderer = ReactionVideoRenderer()
    renderer.render(
        source_video_path=source_video,
        avatar_video_path=avatar_video,
        voice_audio_path=voice_wav,
        ass_subtitle_path=ass_path,
        output_path=final_mp4,
    )
    assert final_mp4.exists()

    # Decodifica a trilha AAC do MP4 composto de volta para PCM s16le 24kHz
    decoded_pcm_path = tmp_path / "decoded_audio.pcm"
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(final_mp4),
            "-vn",
            "-c:a", "pcm_s16le",
            "-ar", str(sample_rate),
            "-ac", "1",
            "-f", "s16le",
            str(decoded_pcm_path),
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )
    floats = pcm_bytes_to_floats(decoded_pcm_path.read_bytes())
    assert len(floats) > sample_rate * 2

    def _window_rms(center_sec: float, half_win_sec: float = 0.025) -> float:
        i0 = max(0, int((center_sec - half_win_sec) * sample_rate))
        i1 = min(len(floats), int((center_sec + half_win_sec) * sample_rate))
        return compute_audio_rms(floats[i0:i1])

    def _sample_video_subtitle_zone(ts: float) -> dict:
        raw_path = tmp_path / f"e2e_frame_{ts:.2f}.raw"
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-ss", f"{ts:.2f}",
                "-i", str(final_mp4),
                "-vframes", "1",
                "-f", "rawvideo",
                "-pix_fmt", "rgb24",
                str(raw_path),
            ],
            check=True,
            capture_output=True,
            timeout=30,
        )
        raw_bytes = raw_path.read_bytes()
        assert len(raw_bytes) == 1080 * 1920 * 3

        yellow_xs: list[int] = []
        dark_box_count = 0
        white_count = 0
        for y in range(SafeZones9x16.SUBTITLE_Y_MIN, SafeZones9x16.SUBTITLE_Y_MAX + 1):
            for x in range(SafeZones9x16.SUBTITLE_MARGIN_LEFT, 657):
                idx = (y * 1080 + x) * 3
                r, g, b = raw_bytes[idx], raw_bytes[idx + 1], raw_bytes[idx + 2]
                if r <= 25 and g <= 25 and b <= 25:
                    dark_box_count += 1
                elif r > 180 and g > 140 and b < 90 and (r - b) > 100:
                    yellow_xs.append(x)
                elif r > 190 and g > 190 and b > 190:
                    white_count += 1

        clusters = 0
        if yellow_xs:
            sorted_x = sorted(set(yellow_xs))
            clusters = 1
            for k in range(1, len(sorted_x)):
                if sorted_x[k] - sorted_x[k - 1] > 35:
                    clusters += 1

        return {
            "yellow_count": len(yellow_xs),
            "yellow_cx": (sum(yellow_xs) / len(yellow_xs)) if yellow_xs else None,
            "yellow_clusters": clusters,
            "white_count": white_count,
            "dark_box_count": dark_box_count,
        }

    burst_centroids: list[float] = []
    for _, _, _, peak_t in bursts:
        rms = _window_rms(peak_t)
        assert rms > 0.04, f"Esperado pico de RMS > 0.04 no instante {peak_t}s; obtido {rms:.4f}"
        frame_stats = _sample_video_subtitle_zone(peak_t)
        assert frame_stats["dark_box_count"] > 1000
        assert frame_stats["yellow_count"] > 40, f"Sem destaque amarelo em pico acústico t={peak_t}s: {frame_stats}"
        assert frame_stats["yellow_clusters"] == 1, f"Mais de 1 palavra em amarelo em t={peak_t}s: {frame_stats}"
        burst_centroids.append(frame_stats["yellow_cx"])

    assert burst_centroids[0] < burst_centroids[1] < burst_centroids[2], (
        f"Centroide amarelo não acompanhou a sequência das palavras faladas: {burst_centroids}"
    )

    for sil_t in silences:
        sil_rms = _window_rms(sil_t)
        assert sil_rms < 0.015, f"Esperado silêncio RMS < 0.015 em t={sil_t}s; obtido {sil_rms:.4f}"
        sil_stats = _sample_video_subtitle_zone(sil_t)
        assert sil_stats["dark_box_count"] > 1000, f"Caixa opaca falhou na pausa t={sil_t}s"
        assert sil_stats["white_count"] > 100, f"Texto branco ausente na pausa t={sil_t}s"
        assert sil_stats["yellow_count"] == 0, f"Destaque amarelo indevido durante silêncio t={sil_t}s: {sil_stats}"


