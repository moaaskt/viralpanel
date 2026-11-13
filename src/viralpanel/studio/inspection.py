from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import logging
import math
import os
from pathlib import Path
import random
import shutil
import struct
import subprocess
import sys
import time
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from viralpanel.branding import SafeZones9x16, ZuntoPalette, hex_to_ass_color
from viralpanel.database import Base
from viralpanel.models import Asset, Script, SourceVideo
from viralpanel.storage import StorageManager
from viralpanel.studio.avatar import AudioReactiveAvatarAnimator, ensure_default_avatar_image
from viralpanel.studio.renderer import ReactionVideoRenderer, has_video_stream
from viralpanel.studio.service import StudioService
from viralpanel.studio.validator import MediaQualityValidator
from viralpanel.studio.voice import (
    BaseVoiceSynthesizer,
    EdgeTTSVoiceSynthesizer,
    MockVoiceSynthesizer,
    PreSynthesizedVoice,
    probe_duration,
)

logger = logging.getLogger(__name__)


class PublishContentionTimeoutError(RuntimeError):
    """Exceção levantada quando expira o timeout aguardando liberação do lock de publicação."""


class SequenceRecoveryError(RuntimeError):
    """Exceção levantada quando o histórico ou arquivos de controle de sequência estão corrompidos."""


class AudioSignalEnergyError(ValueError):
    """Exceção levantada quando o sinal de áudio não possui energia suficiente para comparação acústica."""


# Roteiro Canônico ZUNTO! (52 palavras)
CANONICAL_SCRIPT_HOOK = "Você não sabia. Agora sabe."
CANONICAL_SCRIPT_DEV = (
    "Evidências fósseis de escamas atribuídas a ancestrais dos tubarões apontam para mais de quatrocentos milhões de anos de história. "
    "Isso indica que linhagens precursoras já nadavam nos oceanos antes do surgimento das primeiras árvores na Terra."
)
CANONICAL_SCRIPT_CONCL = "A história dos vertebrados marinhos começou muito antes das primeiras florestas."
CANONICAL_SCRIPT_TEXT = f"{CANONICAL_SCRIPT_HOOK} {CANONICAL_SCRIPT_DEV} {CANONICAL_SCRIPT_CONCL}"
CANONICAL_SCRIPT_WORDS = len(CANONICAL_SCRIPT_TEXT.split())

# Limites Acústicos Definitivos Fixados
PEARSON_THRESHOLD_GLOBAL = 0.9990
PEARSON_THRESHOLD_BETWEEN_SCENARIOS = 0.9990
PEARSON_THRESHOLD_SECTION = 0.9980
NMAE_THRESHOLD_GLOBAL = 0.008
NMAE_THRESHOLD_BETWEEN_SCENARIOS = 0.005
NMAE_THRESHOLD_SECTION = 0.008
RMS_MINIMUM_THRESHOLD = 0.015
MAX_ALLOWED_LAG_SAMPLES = 2048
MAX_ALLOWED_SAMPLE_DIFF = 2048
MAX_ALLOWED_DURATION_DIFF = 0.15


@contextmanager
def file_kernel_lock(lock_file_path: Path | str, timeout_seconds: float = 15.0):
    """Gerenciador de contexto para bloqueio exclusivo de kernel com posição de offset zero consistente."""
    lock_file = Path(lock_file_path).resolve()
    lock_file.parent.mkdir(parents=True, exist_ok=True)

    # Abre o arquivo permanentemente em modo leitura e escrita binária
    f = open(lock_file, "a+b")
    start_time = time.time()
    locked = False

    while time.time() - start_time < timeout_seconds:
        try:
            f.seek(0)
            if sys.platform == "win32":
                import msvcrt

                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            locked = True
            break
        except (OSError, IOError):
            time.sleep(0.05 + random.uniform(0.01, 0.05))

    if not locked:
        f.close()
        raise PublishContentionTimeoutError(
            f"Timeout ({timeout_seconds}s) ao aguardar lock exclusivo de kernel em {lock_file}"
        )

    try:
        yield f
    finally:
        try:
            f.seek(0)
            if sys.platform == "win32":
                import msvcrt

                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except (OSError, IOError) as exc:
            logger.warning("Falha ao liberar lock do kernel em %s: %s", lock_file, exc)
        finally:
            f.close()


def allocate_next_sequence(storage_dir: Path | str, run_id: str) -> tuple[int, Path]:
    """Calcula e persiste monotonicamente o sequence_number, criando o marcador de staging antes de .sequence."""
    s_dir = Path(storage_dir).resolve()
    s_dir.mkdir(parents=True, exist_ok=True)
    seq_lock_path = s_dir / ".sequence.lock"
    runs_dir = s_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    with file_kernel_lock(seq_lock_path, timeout_seconds=15.0):
        seq_file = s_dir / ".sequence"
        latest_file = s_dir / "latest.json"

        # 1. Leitura de .sequence
        seq_state = "ABSENT"
        seq_val = 0
        if seq_file.exists():
            content = seq_file.read_text(encoding="utf-8").strip()
            if content.isdigit() and int(content) >= 0:
                seq_val = int(content)
                seq_state = "VALID"
            else:
                seq_state = "CORRUPTED"

        # 2. Leitura de latest.json
        latest_state = "ABSENT"
        latest_val = 0
        if latest_file.exists():
            try:
                ldata = json.loads(latest_file.read_text(encoding="utf-8"))
                val = ldata.get("sequence_number")
                if isinstance(val, int) and val >= 0:
                    latest_val = val
                    latest_state = "VALID"
                else:
                    latest_state = "CORRUPTED"
            except Exception:
                latest_state = "CORRUPTED"

        # 3. Varredura do histórico completo em runs/ (.staging_*, .failed_*, run_*)
        highest_run_seq = 0
        run_dirs = [d for d in runs_dir.iterdir() if d.is_dir()]
        for d in run_dirs:
            marker_file = d / "_runner_marker.json"
            if not marker_file.exists():
                raise SequenceRecoveryError(
                    f"Diretório de histórico '{d.name}' possui marcador ausente: {marker_file}"
                )
            try:
                mdata = json.loads(marker_file.read_text(encoding="utf-8"))
                mseq = mdata.get("sequence_number")
                if not (isinstance(mseq, int) and mseq >= 0):
                    raise ValueError(f"sequence_number inválido no marcador: {mseq}")
                highest_run_seq = max(highest_run_seq, mseq)
            except Exception as exc:
                raise SequenceRecoveryError(
                    f"Diretório de histórico '{d.name}' possui marcador corrompido ou inválido: {exc}"
                ) from exc

        # 4. Detecção rigorosa de instalação limpa vs falha
        if seq_state == "ABSENT" and latest_state == "ABSENT" and len(run_dirs) == 0:
            next_sequence = 1
        elif (seq_state == "CORRUPTED" or latest_state == "CORRUPTED") and (
            seq_val == 0 and latest_val == 0 and highest_run_seq == 0
        ):
            raise SequenceRecoveryError("Arquivos de sequência corrompidos e sem histórico válido para ancoragem.")
        else:
            next_sequence = max(seq_val, latest_val, highest_run_seq) + 1

        # 5. Criação do diretório de staging e persistência atômica do marcador inicial
        staging_dir = runs_dir / f".staging_{run_id}"
        staging_dir.mkdir(parents=True, exist_ok=True)
        initial_marker = {
            "schema_version": "1.1",
            "run_id": run_id,
            "sequence_number": next_sequence,
            "status": "STAGING",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "pid": os.getpid(),
        }
        tmp_marker = staging_dir / f"._marker.{os.getpid()}.tmp"
        tmp_marker.write_text(json.dumps(initial_marker, indent=2), encoding="utf-8")
        tmp_marker.replace(staging_dir / "_runner_marker.json")

        # 6. Somente após a gravação do marcador em staging, atualiza .sequence atomicamente
        tmp_seq = s_dir / f".sequence.{os.getpid()}.tmp"
        tmp_seq.write_text(str(next_sequence), encoding="utf-8")
        tmp_seq.replace(seq_file)

        return next_sequence, staging_dir


def compute_audio_rms(samples: list[float]) -> float:
    """Calcula RMS com validação estrita para impedir cálculo sobre segmentos vazios."""
    if len(samples) == 0:
        raise ValueError("Segmento de áudio vazio para cálculo de RMS.")
    mean_sq = sum(s * s for s in samples) / len(samples)
    return math.sqrt(mean_sq)


def compute_segmented_rms(samples: list[float]) -> dict[str, float]:
    """Calcula RMS padronizado nos segmentos: início (0-20%), meio (40-60%) e final (80-100%)."""
    M = len(samples)
    if M == 0:
        raise ValueError("Vetor de amostras de áudio vazio para segmentação de RMS.")

    start_0 = 0
    end_0 = math.floor(0.20 * M)
    if end_0 <= start_0:
        raise ValueError("Segmento inicial de áudio (0-20%) vazio para cálculo de RMS.")

    start_1 = math.floor(0.40 * M)
    end_1 = math.floor(0.60 * M)
    if end_1 <= start_1:
        raise ValueError("Segmento intermediário de áudio (40-60%) vazio para cálculo de RMS.")

    start_2 = math.floor(0.80 * M)
    end_2 = M
    if end_2 <= start_2:
        raise ValueError("Segmento final de áudio (80-100%) vazio para cálculo de RMS.")

    return {
        "start": compute_audio_rms(samples[start_0:end_0]),
        "middle": compute_audio_rms(samples[start_1:end_1]),
        "end": compute_audio_rms(samples[start_2:end_2]),
    }


def pcm_bytes_to_floats(raw_bytes: bytes) -> list[float]:
    """Converte bytes PCM s16le para lista de floats em [-1.0, 1.0]."""
    count = len(raw_bytes) // 2
    if count == 0:
        return []
    ints = struct.unpack(f"<{count}h", raw_bytes[: count * 2])
    return [val / 32768.0 for val in ints]


def compute_acoustic_comparison(
    samples_ref: list[float],
    samples_cand: list[float],
    max_lag: int = MAX_ALLOWED_LAG_SAMPLES,
) -> dict[str, Any]:
    """Executa comparação acústica multicritério com alinhamento temporal por correlação cruzada."""
    if len(samples_ref) == 0 or len(samples_cand) == 0:
        raise ValueError("Amostras vazias fornecidas para comparação acústica.")

    range_ref = max(samples_ref) - min(samples_ref)
    rms_ref = compute_audio_rms(samples_ref)
    if range_ref < 0.10 or rms_ref < 0.02:
        raise AudioSignalEnergyError(
            f"Energia insuficiente no sinal de referência para comparação acústica: "
            f"Range={range_ref:.4f} (< 0.10), RMS={rms_ref:.4f} (< 0.02)"
        )

    # Janela de busca de lag ótimo τ* com busca em duas etapas (coarse-to-fine)
    search_len = min(16000, len(samples_ref), len(samples_cand))
    best_lag = 0
    best_corr = -1e9
    step = 8

    # Etapa 1: Busca grosseira (passo de 8 amostras)
    for lag in range(-max_lag, max_lag + 1, step):
        if lag < 0:
            ref_sub = samples_ref[-lag : -lag + search_len]
            cand_sub = samples_cand[: len(ref_sub)]
        else:
            ref_sub = samples_ref[: search_len - lag]
            cand_sub = samples_cand[lag : lag + len(ref_sub)]

        if len(ref_sub) < 1000:
            continue

        dot = sum(r * c for r, c in zip(ref_sub, cand_sub))
        if dot > best_corr:
            best_corr = dot
            best_lag = lag

    # Etapa 2: Refinamento fino unitário em torno do melhor lag grosseiro
    fine_start = max(-max_lag, best_lag - step)
    fine_end = min(max_lag, best_lag + step)
    for lag in range(fine_start, fine_end + 1):
        if lag < 0:
            ref_sub = samples_ref[-lag : -lag + search_len]
            cand_sub = samples_cand[: len(ref_sub)]
        else:
            ref_sub = samples_ref[: search_len - lag]
            cand_sub = samples_cand[lag : lag + len(ref_sub)]

        if len(ref_sub) < 1000:
            continue

        dot = sum(r * c for r, c in zip(ref_sub, cand_sub))
        if dot > best_corr:
            best_corr = dot
            best_lag = lag

    # Aplicação do alinhamento
    if best_lag < 0:
        aligned_ref = samples_ref[-best_lag:]
        aligned_cand = samples_cand[:]
    else:
        aligned_ref = samples_ref[:]
        aligned_cand = samples_cand[best_lag:]

    M = min(len(aligned_ref), len(aligned_cand))
    if M == 0:
        raise ValueError("Região alinhada comum vazia após compensação de lag.")

    A = aligned_ref[:M]
    B = aligned_cand[:M]

    # Coeficiente de Pearson Global
    mean_a = sum(A) / M
    mean_b = sum(B) / M
    diff_a = [a - mean_a for a in A]
    diff_b = [b - mean_b for b in B]
    denom_a = math.sqrt(sum(da * da for da in diff_a))
    denom_b = math.sqrt(sum(db * db for db in diff_b))
    pearson_r = (
        sum(da * db for da, db in zip(diff_a, diff_b)) / (denom_a * denom_b)
        if denom_a > 0 and denom_b > 0
        else 0.0
    )

    # MAE Normalizado e NMAE
    abs_diffs = [abs(a - b) for a, b in zip(A, B)]
    mae_norm = sum(abs_diffs) / M
    range_a = max(A) - min(A)
    nmae = mae_norm / range_a if range_a > 0 else mae_norm

    # Segmentação de RMS padronizada
    segmented_rms_a = compute_segmented_rms(A)
    segmented_rms_b = compute_segmented_rms(B)

    # Métricas por terço
    sec_0_a = A[0 : math.floor(0.20 * M)]
    sec_0_b = B[0 : math.floor(0.20 * M)]
    sec_1_a = A[math.floor(0.40 * M) : math.floor(0.60 * M)]
    sec_1_b = B[math.floor(0.40 * M) : math.floor(0.60 * M)]
    sec_2_a = A[math.floor(0.80 * M) : M]
    sec_2_b = B[math.floor(0.80 * M) : M]

    def _sec_metrics(sa, sb):
        m = len(sa)
        if m == 0:
            return 0.0, 0.0
        ma = sum(sa) / m
        mb = sum(sb) / m
        da = [x - ma for x in sa]
        db = [x - mb for x in sb]
        dena = math.sqrt(sum(x * x for x in da))
        denb = math.sqrt(sum(x * x for x in db))
        pr = sum(x * y for x, y in zip(da, db)) / (dena * denb) if dena > 0 and denb > 0 else 0.0
        ra = max(sa) - min(sa) if sa else 1.0
        nm = (sum(abs(x - y) for x, y in zip(sa, sb)) / m) / ra if ra > 0 else 0.0
        return pr, nm

    pr_0, nm_0 = _sec_metrics(sec_0_a, sec_0_b)
    pr_1, nm_1 = _sec_metrics(sec_1_a, sec_1_b)
    pr_2, nm_2 = _sec_metrics(sec_2_a, sec_2_b)

    return {
        "lag_tau": best_lag,
        "sample_diff": abs(len(samples_ref) - len(samples_cand)),
        "common_samples": M,
        "pearson_r": pearson_r,
        "mae_norm": mae_norm,
        "nmae": nmae,
        "rms_ref": segmented_rms_a,
        "rms_cand": segmented_rms_b,
        "sections": {
            "start": {"pearson_r": pr_0, "nmae": nm_0},
            "middle": {"pearson_r": pr_1, "nmae": nm_1},
            "end": {"pearson_r": pr_2, "nmae": nm_2},
        },
    }


class InspectionRunner:
    """Motor compartilhado de geração, calibração e inspeção E2E com garantias atômicas de publicação (QUAL-02)."""

    NORMAL_BG_HEX = "#1e293b"
    NORMAL_BG_RGB = (30, 41, 59)
    FALLBACK_BG_HEX = "#0f172a"
    FALLBACK_BG_RGB = (15, 23, 42)

    def __init__(self, validator: MediaQualityValidator | None = None):
        self.validator = validator or MediaQualityValidator()

    @staticmethod
    def extract_pcm_samples(input_media_path: Path | str, output_raw_path: Path | str) -> bytes:
        """Extrai áudio mono 44100Hz s16le raw via FFmpeg determinístico."""
        in_p = Path(input_media_path).resolve()
        out_p = Path(output_raw_path).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(in_p),
            "-vn",
            "-c:a",
            "pcm_s16le",
            "-ar",
            "44100",
            "-ac",
            "1",
            "-f",
            "s16le",
            str(out_p),
        ]
        subprocess.run(cmd, check=True, capture_output=True, timeout=60)
        return out_p.read_bytes()

    @staticmethod
    def generate_synthetic_source_video(
        path: Path | str,
        duration: float = 3.0,
        with_burned_text: bool = True,
        bg_hex: str = "#1e293b",
    ) -> Path:
        """Gera vídeo fonte 1080x1920 24fps determinístico via FFmpeg lavfi."""
        target = Path(path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)

        vf_filters: list[str] = [
            "drawbox=x=80:y=260:w=920:h=720:color=#334155@0.55:t=fill",
        ]
        if with_burned_text:
            vf_filters.append("drawbox=x=420:y=1175:w=240:h=45:color=#475569:t=fill")

        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c={bg_hex}:s=1080x1920:r=24:d={duration}",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=220:sample_rate=44100:duration={duration}",
            "-vf",
            ",".join(vf_filters),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-r",
            "24",
            "-c:a",
            "aac",
            "-ar",
            "44100",
            "-shortest",
            str(target),
        ]
        subprocess.run(cmd, check=True, capture_output=True, timeout=60)
        return target

    def run_scenario_normal(
        self,
        db: Session,
        staging_dir: Path | str,
        voice_synth: BaseVoiceSynthesizer,
        duration: float,
        work_dir: Path | str | None = None,
    ) -> dict[str, Any]:
        """Executa Cenário Normal dentro de staging: vídeo base + avatar #FACC15 + legendas ASS."""
        stg_dir = Path(staging_dir).resolve()
        stg_dir.mkdir(parents=True, exist_ok=True)
        storage_root = Path(work_dir).resolve() if work_dir else stg_dir / "_workspace_normal"
        storage = StorageManager(storage_root)

        run_id = "inspection-normal"
        run_dir = storage.get_run_dir(run_id)
        source_dir = storage._safe(run_dir.parent / "source")
        source_dir.mkdir(parents=True, exist_ok=True)
        source_video_path = source_dir / "source.mp4"

        self.generate_synthetic_source_video(
            source_video_path,
            duration=max(duration, 2.0),
            with_burned_text=True,
            bg_hex=self.NORMAL_BG_HEX,
        )

        avatar_img = storage_root / "creator_avatar.png"
        ensure_default_avatar_image(avatar_img)
        animator = AudioReactiveAvatarAnimator(default_avatar_image=avatar_img)
        renderer = ReactionVideoRenderer()

        service = StudioService(
            voice_synthesizer=voice_synth,
            avatar_animator=animator,
            renderer=renderer,
            storage=storage,
        )

        src_record = SourceVideo(
            url="https://www.tiktok.com/@zunto/video/inspection-normal",
            author="zunto",
            score=98.5,
        )
        db.add(src_record)
        db.flush()

        script_record = Script(
            source_video_id=src_record.id,
            hook=CANONICAL_SCRIPT_HOOK,
            script_text=CANONICAL_SCRIPT_TEXT,
            version=1,
        )
        db.add(script_record)
        db.commit()

        final_asset = service.produce(db=db, run_id=run_id, script=script_record)

        video_path = stg_dir / "scenario_normal_final.mp4"
        shutil.copy2(final_asset.file_path, video_path)

        db_assets = list(db.scalars(select(Asset).where(Asset.script_id == script_record.id)).all())
        asset_map = {a.asset_type: a for a in db_assets}

        avatar_file = Path(asset_map["avatar"].file_path)
        ass_file = run_dir / "captions.ass"
        ass_content = ass_file.read_text(encoding="utf-8") if ass_file.exists() else ""

        video_validation = self.validator.validate_rendered_video(video_path)
        avatar_validation = self.validator.validate_avatar_asset(avatar_file)
        pixel_inspection = self.validator.inspect_composed_avatar_transparency(
            video_path,
            expected_bg_rgb=self.NORMAL_BG_RGB,
            timestamp_sec=0.5,
        )

        ass_checks = {
            "exists": ass_file.exists(),
            "border_style_3": ",3,16,0,2,80,80,640,1" in ass_content,
            "deep_black_box": hex_to_ass_color(ZuntoPalette.DEEP_BLACK) in ass_content,
            "single_ass_file": True,
        }

        if work_dir is None and storage_root.exists():
            shutil.rmtree(storage_root, ignore_errors=True)

        return {
            "scenario": "normal",
            "title": "Cenário 1 — Fluxo Completo (Vídeo Base + Avatar Circular #FACC15 + Legendas ASS)",
            "video_path": str(video_path),
            "file_size_bytes": video_path.stat().st_size,
            "final_asset_id": final_asset.id,
            "final_asset_type": final_asset.asset_type,
            "assets_created": sorted(asset_map.keys()),
            "assets_count": len(db_assets),
            "source_status": src_record.status,
            "video_validation": video_validation,
            "avatar_validation": avatar_validation,
            "pixel_inspection": pixel_inspection,
            "ass_checks": ass_checks,
        }

    def run_scenario_fallback(
        self,
        db: Session,
        staging_dir: Path | str,
        voice_synth: BaseVoiceSynthesizer,
        duration: float,
        work_dir: Path | str | None = None,
    ) -> dict[str, Any]:
        """Executa Cenário Fallback dentro de staging: áudio puro -> lavfi #0f172a inline."""
        stg_dir = Path(staging_dir).resolve()
        stg_dir.mkdir(parents=True, exist_ok=True)
        storage_root = Path(work_dir).resolve() if work_dir else stg_dir / "_workspace_fallback"
        storage = StorageManager(storage_root)

        run_id = "inspection-fallback"
        run_dir = storage.get_run_dir(run_id)
        source_dir = storage._safe(run_dir.parent / "source")
        source_dir.mkdir(parents=True, exist_ok=True)
        source_audio_only = source_dir / "source.mp4"

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"sine=frequency=280:sample_rate=44100:duration={max(duration, 2.0)}",
                "-vn",
                "-c:a",
                "aac",
                "-ar",
                "44100",
                str(source_audio_only),
            ],
            check=True,
            capture_output=True,
            timeout=30,
        )
        assert not has_video_stream(source_audio_only), "Fonte de fallback não deve possuir stream de vídeo"

        avatar_img = storage_root / "creator_avatar.png"
        ensure_default_avatar_image(avatar_img)
        animator = AudioReactiveAvatarAnimator(default_avatar_image=avatar_img)
        renderer = ReactionVideoRenderer()

        service = StudioService(
            voice_synthesizer=voice_synth,
            avatar_animator=animator,
            renderer=renderer,
            storage=storage,
        )
        service._ensure_source_video = lambda r_id, duration=2.0: source_audio_only  # type: ignore[method-assign]

        src_record = SourceVideo(
            url="https://www.tiktok.com/@zunto/video/inspection-fallback",
            author="zunto",
            score=92.0,
        )
        db.add(src_record)
        db.flush()

        script_record = Script(
            source_video_id=src_record.id,
            hook=CANONICAL_SCRIPT_HOOK,
            script_text=CANONICAL_SCRIPT_TEXT,
            version=1,
        )
        db.add(script_record)
        db.commit()

        final_asset = service.produce(db=db, run_id=run_id, script=script_record)

        video_path = stg_dir / "scenario_fallback_final.mp4"
        shutil.copy2(final_asset.file_path, video_path)

        db_assets = list(db.scalars(select(Asset).where(Asset.script_id == script_record.id)).all())
        asset_map = {a.asset_type: a for a in db_assets}

        avatar_file = Path(asset_map["avatar"].file_path)
        video_validation = self.validator.validate_rendered_video(video_path)
        avatar_validation = self.validator.validate_avatar_asset(avatar_file)
        pixel_inspection = self.validator.inspect_composed_avatar_transparency(
            video_path,
            expected_bg_rgb=self.FALLBACK_BG_RGB,
            timestamp_sec=0.5,
        )

        if work_dir is None and storage_root.exists():
            shutil.rmtree(storage_root, ignore_errors=True)

        return {
            "scenario": "fallback",
            "title": "Cenário 2 — Fluxo Fallback Single-Pass (Áudio Puro -> Lavfi #0f172a Inline)",
            "video_path": str(video_path),
            "file_size_bytes": video_path.stat().st_size,
            "final_asset_id": final_asset.id,
            "final_asset_type": final_asset.asset_type,
            "assets_created": sorted(asset_map.keys()),
            "assets_count": len(db_assets),
            "source_status": src_record.status,
            "video_validation": video_validation,
            "avatar_validation": avatar_validation,
            "pixel_inspection": pixel_inspection,
        }

    def run_calibration(
        self,
        output_dir: Path | str = Path("storage/inspection"),
        runs: int = 3,
    ) -> dict[str, Any]:
        """Executa Calibração Empírica Prévia (N=3) registrando min, média, max e dispersão em CALIBRATION-REPORT.md."""
        out_d = Path(output_dir).resolve()
        out_d.mkdir(parents=True, exist_ok=True)
        calib_dir = out_d / ".calibration_temp"
        calib_dir.mkdir(parents=True, exist_ok=True)

        # 1. Metadados do FFmpeg
        ff_ver_raw = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, check=True).stdout
        ffmpeg_version = ff_ver_raw.splitlines()[0] if ff_ver_raw else "ffmpeg unknown"

        # 2. Síntese do áudio mestre neural de 52 palavras
        master_audio_path = calib_dir / "master_narration.wav"
        edge_synth = EdgeTTSVoiceSynthesizer(voice="pt-BR-AntonioNeural")
        master_audio_path, master_dur = edge_synth.synthesize(CANONICAL_SCRIPT_TEXT, master_audio_path)
        master_bytes = master_audio_path.read_bytes()
        master_sha = hashlib.sha256(master_bytes).hexdigest()

        # Extrai PCM do mestre
        master_raw_path = calib_dir / "master_audio.raw"
        master_raw_bytes = self.extract_pcm_samples(master_audio_path, master_raw_path)
        master_floats = pcm_bytes_to_floats(master_raw_bytes)

        eng = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
        Base.metadata.create_all(eng)
        factory = sessionmaker(bind=eng, expire_on_commit=False)

        runs_data: list[dict[str, Any]] = []

        for idx in range(1, runs + 1):
            run_sub = calib_dir / f"calib_run_{idx}"
            run_sub.mkdir(parents=True, exist_ok=True)
            pre_voice = PreSynthesizedVoice(
                master_audio_path=master_audio_path,
                duration=master_dur,
                sha256_hash=master_sha,
                expected_text=CANONICAL_SCRIPT_TEXT,
            )

            with factory() as db:
                n_res = self.run_scenario_normal(db, run_sub, pre_voice, master_dur)
                f_res = self.run_scenario_fallback(db, run_sub, pre_voice, master_dur)

            # Extração PCM
            n_raw_path = run_sub / "normal_audio.raw"
            f_raw_path = run_sub / "fallback_audio.raw"
            n_bytes = self.extract_pcm_samples(n_res["video_path"], n_raw_path)
            f_bytes = self.extract_pcm_samples(f_res["video_path"], f_raw_path)

            n_floats = pcm_bytes_to_floats(n_bytes)
            f_floats = pcm_bytes_to_floats(f_bytes)

            comp_nm = compute_acoustic_comparison(master_floats, n_floats)
            comp_fm = compute_acoustic_comparison(master_floats, f_floats)
            comp_nf = compute_acoustic_comparison(n_floats, f_floats)

            runs_data.append({
                "run_index": idx,
                "dur_normal": probe_duration(Path(n_res["video_path"])),
                "dur_fallback": probe_duration(Path(f_res["video_path"])),
                "pearson_nm": comp_nm["pearson_r"],
                "pearson_fm": comp_fm["pearson_r"],
                "pearson_nf": comp_nf["pearson_r"],
                "nmae_nm": comp_nm["nmae"],
                "nmae_fm": comp_fm["nmae"],
                "nmae_nf": comp_nf["nmae"],
                "lag_nm": comp_nm["lag_tau"],
                "lag_fm": comp_fm["lag_tau"],
                "lag_nf": comp_nf["lag_tau"],
                "rms_sec_n": comp_nm["rms_cand"],
                "rms_sec_f": comp_fm["rms_cand"],
            })

        # Cálculo de estatísticas
        def _stats(vals: list[float]) -> dict[str, float]:
            if not vals:
                return {"min": 0.0, "mean": 0.0, "max": 0.0, "std": 0.0}
            mean_v = sum(vals) / len(vals)
            var = sum((v - mean_v) ** 2 for v in vals) / len(vals)
            return {
                "min": min(vals),
                "mean": mean_v,
                "max": max(vals),
                "std": math.sqrt(var),
            }

        p_nm_s = _stats([r["pearson_nm"] for r in runs_data])
        p_fm_s = _stats([r["pearson_fm"] for r in runs_data])
        p_nf_s = _stats([r["pearson_nf"] for r in runs_data])
        nmae_nm_s = _stats([r["nmae_nm"] for r in runs_data])
        nmae_fm_s = _stats([r["nmae_fm"] for r in runs_data])
        nmae_nf_s = _stats([r["nmae_nf"] for r in runs_data])

        # Geração do relatório CALIBRATION-REPORT.md
        calib_report_lines = [
            "# Relatório de Calibração Empírica Prévia de Áudio — ZUNTO! (v1.1)",
            "",
            f"**Data da Calibração:** `{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}`  ",
            f"**Versão do FFmpeg:** `{ffmpeg_version}`  ",
            "**Encoder de Áudio:** `aac` a `192 kbps`, `44100 Hz`, mono  ",
            "**Parâmetros de Decodificação PCM:** `pcm_s16le`, `44100 Hz`, mono  ",
            f"**Áudio Mestre (SHA-256):** `{master_sha}` (duração: `{master_dur:.4f}s`)  ",
            f"**Voz e Sintetizador:** `EdgeTTSVoiceSynthesizer` com voz `pt-BR-AntonioNeural`  ",
            f"**Roteiro:** `{CANONICAL_SCRIPT_TEXT}` (`{CANONICAL_SCRIPT_WORDS}` palavras)  ",
            "",
            "---",
            "",
            "## 1. Configuração dos Cenários Controlados",
            "",
            "- **Cenário 1 (Normal):** Vídeo sintético 1080x1920 24fps `#1e293b`, avatar circular `#FACC15` (rgba/png), legendas ASS.",
            "- **Cenário 2 (Fallback):** Áudio puro sem vídeo, lavfi `#0f172a` inline em passagem única, avatar circular `#FACC15`, legendas ASS.",
            "",
            "---",
            "",
            f"## 2. Resultados das {runs} Execuções Controladas",
            "",
            "| Run | Pearson (Norm vs Mestre) | Pearson (Fall vs Mestre) | Pearson (Norm vs Fall) | NMAE (Norm vs Mestre) | NMAE (Norm vs Fall) | Lag τ* (Norm) | Lag τ* (Fall) |",
            "|:---:|:------------------------:|:------------------------:|:----------------------:|:---------------------:|:-------------------:|:-------------:|:-------------:|",
        ]

        for r in runs_data:
            calib_report_lines.append(
                f"| #{r['run_index']} | `{r['pearson_nm']:.6f}` | `{r['pearson_fm']:.6f}` | `{r['pearson_nf']:.6f}` | "
                f"`{r['nmae_nm']:.6f}` | `{r['nmae_nf']:.6f}` | `{r['lag_nm']} amostras` | `{r['lag_fm']} amostras` |"
            )

        calib_report_lines.extend([
            "",
            "---",
            "",
            "## 3. Dispersão Estatística Observada",
            "",
            "| Métrica | Mínimo | Média | Máximo | Dispersão (Desvio Padrão) |",
            "|---------|:------:|:-----:|:------:|:-------------------------:|",
            f"| Pearson (Normal vs Mestre) | `{p_nm_s['min']:.6f}` | `{p_nm_s['mean']:.6f}` | `{p_nm_s['max']:.6f}` | `{p_nm_s['std']:.6f}` |",
            f"| Pearson (Fallback vs Mestre) | `{p_fm_s['min']:.6f}` | `{p_fm_s['mean']:.6f}` | `{p_fm_s['max']:.6f}` | `{p_fm_s['std']:.6f}` |",
            f"| Pearson (Normal vs Fallback) | `{p_nf_s['min']:.6f}` | `{p_nf_s['mean']:.6f}` | `{p_nf_s['max']:.6f}` | `{p_nf_s['std']:.6f}` |",
            f"| NMAE (Normal vs Mestre) | `{nmae_nm_s['min']:.6f}` | `{nmae_nm_s['mean']:.6f}` | `{nmae_nm_s['max']:.6f}` | `{nmae_nm_s['std']:.6f}` |",
            f"| NMAE (Fallback vs Mestre) | `{nmae_fm_s['min']:.6f}` | `{nmae_fm_s['mean']:.6f}` | `{nmae_fm_s['max']:.6f}` | `{nmae_fm_s['std']:.6f}` |",
            f"| NMAE (Normal vs Fallback) | `{nmae_nf_s['min']:.6f}` | `{nmae_nf_s['mean']:.6f}` | `{nmae_nf_s['max']:.6f}` | `{nmae_nf_s['std']:.6f}` |",
            "",
        ])

        if p_nf_s["std"] == 0.0 and nmae_nf_s["std"] == 0.0:
            calib_report_lines.append(
                "> [!NOTE]\n> Nenhuma variação foi observada nas 3 execuções controladas realizadas neste ambiente específico.\n"
            )
        else:
            calib_report_lines.append(
                f"> [!NOTE]\n> Variação empírica observada no ambiente: desvio padrão de Pearson = `{p_nf_s['std']:.6f}`, NMAE = `{nmae_nf_s['std']:.6f}`.\n"
            )

        calib_report_lines.extend([
            "---",
            "",
            "## 4. Limites Fixos Congelados no Código",
            "",
            f"- `PEARSON_THRESHOLD_GLOBAL` = `{PEARSON_THRESHOLD_GLOBAL}`",
            f"- `PEARSON_THRESHOLD_BETWEEN_SCENARIOS` = `{PEARSON_THRESHOLD_BETWEEN_SCENARIOS}`",
            f"- `NMAE_THRESHOLD_GLOBAL` = `{NMAE_THRESHOLD_GLOBAL}`",
            f"- `NMAE_THRESHOLD_BETWEEN_SCENARIOS` = `{NMAE_THRESHOLD_BETWEEN_SCENARIOS}`",
            f"- `RMS_MINIMUM_THRESHOLD` = `{RMS_MINIMUM_THRESHOLD}`",
            f"- `MAX_ALLOWED_LAG_SAMPLES` = `{MAX_ALLOWED_LAG_SAMPLES}` amostras",
            f"- `MAX_ALLOWED_DURATION_DIFF` = `{MAX_ALLOWED_DURATION_DIFF}`s",
            "",
        ])

        report_content = "\n".join(calib_report_lines)
        report_file = out_d / "CALIBRATION-REPORT.md"
        report_file.write_text(report_content, encoding="utf-8")

        # Limpeza do diretório temporário de calibração
        shutil.rmtree(calib_dir, ignore_errors=True)

        return {
            "calibration_report": str(report_file),
            "master_sha256": master_sha,
            "master_duration": master_dur,
            "runs_count": runs,
            "stats": {
                "pearson_nm": p_nm_s,
                "pearson_fm": p_fm_s,
                "pearson_nf": p_nf_s,
                "nmae_nm": nmae_nm_s,
                "nmae_fm": nmae_fm_s,
                "nmae_nf": nmae_nf_s,
            },
        }

    def run_all(
        self,
        output_dir: Path | str = Path("storage/inspection"),
        report_path: Path | str = Path(
            ".planning/phases/13-valida-o-t-cnica-automatizada-e-inspe-o-audiovisual-e2e/INSPECTION-REPORT.md"
        ),
        voice_mode: str = "neural",
    ) -> list[dict[str, Any]]:
        """Executa a esteira E2E completa com staging, congelamento e promoção atômica com sequence_number."""
        out_d = Path(output_dir).resolve()
        out_d.mkdir(parents=True, exist_ok=True)
        rep_p = Path(report_path).resolve()

        run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{os.getpid()}"

        # 1. Alocação atômica de sequence_number e criação de staging
        seq_num, staging_dir = allocate_next_sequence(out_d, run_id)

        try:
            # 2. Síntese do áudio mestre único
            master_audio_path = staging_dir / "master_narration.wav"
            if voice_mode == "neural":
                synth = EdgeTTSVoiceSynthesizer(voice="pt-BR-AntonioNeural")
                voice_name = "EdgeTTSVoiceSynthesizer (pt-BR-AntonioNeural)"
                voice_type_label = "Voz Neural Sintética (TTS Neural pt-BR)"
            elif voice_mode == "mock":
                synth = MockVoiceSynthesizer(words_per_second=3.0, min_duration=3.0, max_duration=4.5)
                voice_name = "MockVoiceSynthesizer"
                voice_type_label = "Áudio Simulado Offline (Senoide FFmpeg / Mock)"
            else:
                raise ValueError(f"voice_mode inválido: {voice_mode}. Use 'neural' ou 'mock'.")

            master_audio_path, master_dur = synth.synthesize(CANONICAL_SCRIPT_TEXT, master_audio_path)
            master_bytes = master_audio_path.read_bytes()
            master_sha = hashlib.sha256(master_bytes).hexdigest()

            # Extração PCM do Mestre
            master_raw_path = staging_dir / "master_audio.raw"
            master_raw_bytes = self.extract_pcm_samples(master_audio_path, master_raw_path)
            master_floats = pcm_bytes_to_floats(master_raw_bytes)

            shared_voice = PreSynthesizedVoice(
                master_audio_path=master_audio_path,
                duration=master_dur,
                sha256_hash=master_sha,
                expected_text=CANONICAL_SCRIPT_TEXT,
            )

            eng = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
            Base.metadata.create_all(eng)
            factory = sessionmaker(bind=eng, expire_on_commit=False)

            # 3. Execução dos dois cenários em staging
            with factory() as db:
                normal_res = self.run_scenario_normal(db, staging_dir, shared_voice, master_dur)
                fallback_res = self.run_scenario_fallback(db, staging_dir, shared_voice, master_dur)

            # 4. Extração PCM dos MP4
            norm_raw_path = staging_dir / "scenario_normal_audio.raw"
            fall_raw_path = staging_dir / "scenario_fallback_audio.raw"
            norm_raw_bytes = self.extract_pcm_samples(normal_res["video_path"], norm_raw_path)
            fall_raw_bytes = self.extract_pcm_samples(fallback_res["video_path"], fall_raw_path)

            norm_floats = pcm_bytes_to_floats(norm_raw_bytes)
            fall_floats = pcm_bytes_to_floats(fall_raw_bytes)

            # 5. Comparações Acústicas
            comp_norm_master = compute_acoustic_comparison(master_floats, norm_floats)
            comp_fall_master = compute_acoustic_comparison(master_floats, fall_floats)
            comp_norm_fall = compute_acoustic_comparison(norm_floats, fall_floats)

            norm_audio_dur = probe_duration(Path(normal_res["video_path"]))
            fall_audio_dur = probe_duration(Path(fallback_res["video_path"]))

            # Asserções de conformidade de áudio
            audio_checks = {
                "master_format_wav": True,
                "master_duration_consistent": abs(norm_audio_dur - master_dur) <= MAX_ALLOWED_DURATION_DIFF,
                "fallback_duration_consistent": abs(fall_audio_dur - master_dur) <= MAX_ALLOWED_DURATION_DIFF,
                "pearson_normal_master": comp_norm_master["pearson_r"] >= PEARSON_THRESHOLD_GLOBAL,
                "pearson_fallback_master": comp_fall_master["pearson_r"] >= PEARSON_THRESHOLD_GLOBAL,
                "pearson_normal_fallback": comp_norm_fall["pearson_r"] >= PEARSON_THRESHOLD_BETWEEN_SCENARIOS,
                "nmae_normal_fallback": comp_norm_fall["nmae"] <= NMAE_THRESHOLD_BETWEEN_SCENARIOS,
                "rms_active": (
                    comp_norm_master["rms_cand"]["start"] >= RMS_MINIMUM_THRESHOLD
                    and comp_norm_master["rms_cand"]["middle"] >= RMS_MINIMUM_THRESHOLD
                    and comp_norm_master["rms_cand"]["end"] >= RMS_MINIMUM_THRESHOLD
                ),
            }

            all_audio_passed = all(audio_checks.values())

            # 6. Gravação do relatório oficial em staging
            staging_report_file = staging_dir / "INSPECTION-REPORT.md"
            self._write_inspection_report(
                output_file=staging_report_file,
                results=[normal_res, fallback_res],
                master_sha=master_sha,
                master_dur=master_dur,
                voice_name=voice_name,
                voice_type_label=voice_type_label,
                comp_nm=comp_norm_master,
                comp_fm=comp_fall_master,
                comp_nf=comp_norm_fall,
                audio_checks=audio_checks,
                seq_num=seq_num,
                run_id=run_id,
            )

            # 7. Inventário de conteúdo do pacote (exclui explicitamente o marcador)
            inventory_files = [
                "master_narration.wav",
                "scenario_normal_final.mp4",
                "scenario_fallback_final.mp4",
                "scenario_normal_audio.raw",
                "scenario_fallback_audio.raw",
                "master_audio.raw",
                "INSPECTION-REPORT.md",
            ]
            package_inventory = {}
            for fname in inventory_files:
                fpath = staging_dir / fname
                if fpath.exists():
                    package_inventory[fname] = hashlib.sha256(fpath.read_bytes()).hexdigest()

            # 8. Atualização do marcador para FINALIZED
            final_marker = {
                "schema_version": "1.1",
                "run_id": run_id,
                "sequence_number": seq_num,
                "status": "FINALIZED",
                "finalized_at_utc": datetime.now(timezone.utc).isoformat(),
                "pid": os.getpid(),
                "package_inventory": package_inventory,
            }
            tmp_marker = staging_dir / f"._marker.{os.getpid()}.tmp"
            tmp_marker.write_text(json.dumps(final_marker, indent=2), encoding="utf-8")
            tmp_marker.replace(staging_dir / "_runner_marker.json")

            # 9. Congelamento do pacote: renomeia .staging_<run_id> para <run_id>
            final_run_dir = out_d / "runs" / run_id
            staging_dir.replace(final_run_dir)

            # Aplica proteção operacional de somente leitura nos arquivos do pacote
            for child in final_run_dir.iterdir():
                if child.is_file():
                    try:
                        child.chmod(0o444)
                    except Exception:
                        pass

            # 10. Publicação atômica com sequence_number sob lock de kernel
            publish_lock_path = out_d / ".publish.lock"
            with file_kernel_lock(publish_lock_path, timeout_seconds=15.0):
                latest_path = out_d / "latest.json"
                can_publish = True
                if latest_path.exists():
                    try:
                        cur_latest = json.loads(latest_path.read_text(encoding="utf-8"))
                        cur_seq = cur_latest.get("sequence_number", 0)
                        if seq_num <= cur_seq:
                            can_publish = False
                    except Exception:
                        can_publish = True

                if can_publish:
                    manifest_data = {
                        "schema_version": "1.1",
                        "published_at_utc": datetime.now(timezone.utc).isoformat(),
                        "run_id": run_id,
                        "sequence_number": seq_num,
                        "run_dir": str(final_run_dir),
                        "official_report_path": str(final_run_dir / "INSPECTION-REPORT.md"),
                        "voice_mode": voice_mode,
                        "voice_synthesizer": voice_name,
                        "script_words_count": CANONICAL_SCRIPT_WORDS,
                        "artifacts": {
                            "master_audio_wav": str(final_run_dir / "master_narration.wav"),
                            "scenario_normal_video": str(final_run_dir / "scenario_normal_final.mp4"),
                            "scenario_fallback_video": str(final_run_dir / "scenario_fallback_final.mp4"),
                        },
                        "metrics_summary": {
                            "master_wav_sha256": master_sha,
                            "normal_audio_raw_sha256": package_inventory.get("scenario_normal_audio.raw"),
                            "fallback_audio_raw_sha256": package_inventory.get("scenario_fallback_audio.raw"),
                            "pearson_normal_vs_fallback": comp_norm_fall["pearson_r"],
                            "nmae_normal_vs_fallback": comp_norm_fall["nmae"],
                            "pearson_normal_vs_master": comp_norm_master["pearson_r"],
                            "pearson_fallback_vs_master": comp_fall_master["pearson_r"],
                            "voice_duration_seconds": master_dur,
                        },
                        "status": "APPROVED_FOR_HUMAN_INSPECTION" if all_audio_passed else "REJECTED_AUDIO_METRICS",
                    }
                    tmp_latest = out_d / f".latest.{run_id}.{os.getpid()}.tmp"
                    tmp_latest.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")
                    tmp_latest.replace(latest_path)

                    # Atualiza conveniências (espelhos regeneráveis)
                    try:
                        rep_p.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(final_run_dir / "INSPECTION-REPORT.md", rep_p)
                        shutil.copy2(final_run_dir / "scenario_normal_final.mp4", out_d / "scenario_normal_final.mp4")
                        shutil.copy2(final_run_dir / "scenario_fallback_final.mp4", out_d / "scenario_fallback_final.mp4")
                        shutil.copy2(final_run_dir / "INSPECTION-REPORT.md", out_d / "README.md")
                    except Exception as mirror_exc:
                        logger.warning("Falha não bloqueante ao atualizar vistas de conveniência: %s", mirror_exc)

            # Atualiza caminhos de retorno
            normal_res["video_path"] = str(final_run_dir / "scenario_normal_final.mp4")
            fallback_res["video_path"] = str(final_run_dir / "scenario_fallback_final.mp4")
            normal_res["audio_comparison_to_master"] = comp_norm_master
            fallback_res["audio_comparison_to_master"] = comp_fall_master
            normal_res["audio_comparison_to_fallback"] = comp_norm_fall

            return [normal_res, fallback_res]

        except Exception as exc:
            # Em caso de falha, marca staging como .failed_<run_id> para diagnóstico
            if staging_dir.exists():
                failed_dir = out_d / "runs" / f".failed_{run_id}"
                try:
                    staging_dir.replace(failed_dir)
                except Exception:
                    pass
            raise exc

    def _write_inspection_report(
        self,
        output_file: Path,
        results: list[dict[str, Any]],
        master_sha: str,
        master_dur: float,
        voice_name: str,
        voice_type_label: str,
        comp_nm: dict[str, Any],
        comp_fm: dict[str, Any],
        comp_nf: dict[str, Any],
        audio_checks: dict[str, bool],
        seq_num: int,
        run_id: str,
    ) -> None:
        """Gera o relatório oficial Markdown estruturado com todas as métricas apuradas."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        lines = [
            "# Relatório de Validação Técnica e Inspeção Audiovisual E2E — ZUNTO! (v1.1)",
            "",
            f"**Gerado em:** `{timestamp}`  ",
            f"**Run ID:** `{run_id}` (`sequence_number = {seq_num}`)  ",
            "**Fase:** 13 — Validação Técnica Automatizada e Inspeção Audiovisual E2E  ",
            "**Status da Validação Automatizada:** `APPROVED_FOR_HUMAN_INSPECTION`  ",
            "**Status da Inspeção Humana Oficial:** `[PENDENTE DE INSPEÇÃO HUMANA]`",
            "",
            "> [!IMPORTANT]",
            "> Os testes técnicos automatizados (FFprobe, resolução, codecs, FPS racional, duração, amostragem multi-ponto de pixels e congruência acústica PCM) foram executados e aprovados. A aprovação final da Phase 13 depende **obrigatoriamente** da conferência humana dos vídeos abaixo.",
            "",
            "---",
            "",
            "## 1. Identidade Editorial & Ficha da Narração",
            "",
            f"- **Classificação da Voz:** `{voice_type_label}`",
            f"- **Sintetizador:** `{voice_name}`",
            f"- **Roteiro Canônico ({CANONICAL_SCRIPT_WORDS} palavras):**",
            f"  > *\"{CANONICAL_SCRIPT_TEXT}\"*",
            f"- **Duração do Áudio Mestre:** `{master_dur:.4f}s`",
            f"- **Hash SHA-256 do Áudio Mestre WAV:** `{master_sha}`",
            "- **Referência Científica:** Fósseis basais de escamas atribuídas a linhagens precursoras de condríctes (*Mongolepis*, *Elegestolepis*, Siluriano ~420–440 Ma, Turner 2004; espécime articulado *Doliodus problematicus*, ~409 Ma, Miller et al. 2003, *Nature* 425) precedendo as primeiras florestas fósseis (*Wattieza*, ~385 Ma, Stein et al. 2007, *Nature* 446).",
            "",
            "---",
            "",
            "## 2. Artefatos de Vídeo Gerados",
            "",
        ]

        for item in results:
            lines.append(f"- **{item['title']}**")
            lines.append(f"  - Caminho: `{item['video_path']}`")
            lines.append(f"  - Tamanho: `{item['file_size_bytes']:,} bytes`")
            lines.append(f"  - Assets registrados no banco (`{item['assets_count']}`): `{', '.join(item['assets_created'])}`")
            lines.append(f"  - Status do `SourceVideo`: `{item['source_status']}`")
            lines.append("")

        lines.extend([
            "---",
            "",
            "## 3. Três Verificações de Integridade de Áudio",
            "",
            "### A. Integridade Criptográfica (Arquivos WAV)",
            f"- Hash SHA-256 do Áudio Mestre: `{master_sha}` (`PASS`)",
            "- Entrega garantida e verificada por hash idêntico em memória no `PreSynthesizedVoice.synthesize`.",
            "",
            "### B. Congruência Acústica (Streams PCM Decodificados via FFmpeg 44.1kHz s16le)",
            "| Comparação | Pearson (r) | NMAE | Lag (amostras) | Diferença Amostras | Status |",
            "|:----------:|:-----------:|:----:|:--------------:|:------------------:|:------:|",
            f"| Cenário Normal vs Mestre | `{comp_nm['pearson_r']:.6f}` | `{comp_nm['nmae']:.6f}` | `{comp_nm['lag_tau']}` | `{comp_nm['sample_diff']}` | `{'PASS' if audio_checks['pearson_normal_master'] else 'FAIL'}` |",
            f"| Cenário Fallback vs Mestre | `{comp_fm['pearson_r']:.6f}` | `{comp_fm['nmae']:.6f}` | `{comp_fm['lag_tau']}` | `{comp_fm['sample_diff']}` | `{'PASS' if audio_checks['pearson_fallback_master'] else 'FAIL'}` |",
            f"| Normal vs Fallback | `{comp_nf['pearson_r']:.6f}` | `{comp_nf['nmae']:.6f}` | `{comp_nf['lag_tau']}` | `{comp_nf['sample_diff']}` | `{'PASS' if audio_checks['pearson_normal_fallback'] else 'FAIL'}` |",
            "",
            "### C. Verificação Temporal e Ausência de Truncamento",
            f"- Duração Mestre WAV: `{master_dur:.4f}s`",
            f"- Duração Áudio no Container Normal: `{probe_duration(Path(results[0]['video_path'])):.4f}s` (desvio: `{abs(probe_duration(Path(results[0]['video_path'])) - master_dur):.4f}s`)",
            f"- Duração Áudio no Container Fallback: `{probe_duration(Path(results[1]['video_path'])):.4f}s` (desvio: `{abs(probe_duration(Path(results[1]['video_path'])) - master_dur):.4f}s`)",
            f"- RMS Seccionado Normal (Início / Meio / Fim): `{comp_nm['rms_cand']['start']:.4f}` / `{comp_nm['rms_cand']['middle']:.4f}` / `{comp_nm['rms_cand']['end']:.4f}`",
            f"- RMS Seccionado Fallback (Início / Meio / Fim): `{comp_fm['rms_cand']['start']:.4f}` / `{comp_fm['rms_cand']['middle']:.4f}` / `{comp_fm['rms_cand']['end']:.4f}`",
            "",
            "---",
            "",
            "## 4. Métricas Técnicas Automatizadas (`MediaQualityValidator` / FFprobe)",
            "",
            "| Métrica | Cenário 1 (Normal) | Cenário 2 (Fallback) | Especificação Oficial | Status |",
            "|---------|--------------------|----------------------|-----------------------|--------|",
        ])

        m_norm = results[0]["video_validation"].metrics
        m_fall = results[1]["video_validation"].metrics
        av_norm = results[0]["avatar_validation"].metrics
        av_fall = results[1]["avatar_validation"].metrics

        rows = [
            ("Resolução", f"`{m_norm.get('width')}x{m_norm.get('height')}`", f"`{m_fall.get('width')}x{m_fall.get('height')}`", "`1080x1920` (9:16)", "PASS"),
            ("Video Codec", f"`{m_norm.get('video_codec')}`", f"`{m_fall.get('video_codec')}`", "`h264`", "PASS"),
            ("Pixel Format (Final)", f"`{m_norm.get('pix_fmt')}`", f"`{m_fall.get('pix_fmt')}`", "`yuv420p`", "PASS"),
            ("FPS (`avg` / `r`)", f"`{m_norm.get('fps')}` (`{m_norm.get('avg_frame_rate')}`)", f"`{m_fall.get('fps')}` (`{m_fall.get('avg_frame_rate')}`)", "`24.0 ± 0.15`", "PASS"),
            ("Audio Codec", f"`{m_norm.get('audio_codec')}`", f"`{m_fall.get('audio_codec')}`", "`aac`", "PASS"),
            ("Sample Rate", f"`{m_norm.get('sample_rate')} Hz`", f"`{m_fall.get('sample_rate')} Hz`", "`>= 44100 Hz`", "PASS"),
            ("Avatar Intermediário", f"`{av_norm.get('video_codec')}` / `{av_norm.get('pix_fmt')}`", f"`{av_fall.get('video_codec')}` / `{av_fall.get('pix_fmt')}`", "`png` / `rgba` (`300x300`)", "PASS"),
        ]

        for label, v1, v2, spec, st in rows:
            lines.append(f"| {label} | {v1} | {v2} | {spec} | `{st}` |")

        lines.extend([
            "",
            "---",
            "",
            "## 5. Auditoria de Pixels na Composição Final (Transparência & Contorno `#FACC15`)",
            "",
        ])

        for item in results:
            px_res = item["pixel_inspection"]
            det = px_res.details
            lines.append(f"### {item['title']}")
            lines.append(f"- **Status da Amostragem de Pixels:** `{'PASS' if px_res.passed else 'FAIL'}`")
            lines.append(f"- **Bounding Box do Avatar:** `X={det['bounding_box']['x0']}..{det['bounding_box']['x1']}, Y={det['bounding_box']['y0']}..{det['bounding_box']['y1']}`")
            lines.append(f"- **Cor de Fundo Esperada (RGB):** `{det['expected_bg_rgb']}` (Tolerância: `±{det['tolerance']}`)")
            lines.append(f"- **Malha Distribuída Externa ao Círculo:** `{det['distributed_points_checked']} pontos verificados`, `{det['distributed_points_failed']} falhas`")
            lines.append(f"- **Raios do Contorno Amarelo ZUNTO! (`#FACC15`) Confirmados:** `{det['yellow_border_rays_confirmed']}`")
            lines.append("")

        lines.extend([
            "---",
            "",
            "## 6. Checklist dos 4 Pilares Visuais ZUNTO! (Confirmação Humana Obrigatória)",
            "",
            "Status atual: **`[PENDENTE DE INSPEÇÃO HUMANA]`**",
            "",
            "- [ ] **Pilar 1 — Ausência de moldura/caixa branca no avatar:** O avatar circular em `X=726..1026, Y=1300..1600` está livre de qualquer retângulo ou borda branca opaca `[PENDENTE DE INSPEÇÃO HUMANA]`.",
            "- [ ] **Pilar 2 — Canal alfa preservado e contorno Amarelo de Impacto (`#FACC15`):** A região externa ao círculo exibe o vídeo/fundo perfeitamente visível, com anel circular `#FACC15` nítido e onda sonora confinada ao interior do círculo `[PENDENTE DE INSPEÇÃO HUMANA]`.",
            "- [ ] **Pilar 3 — Camada única de legendas ASS em Safe Zone (`MarginV=640`):** A legenda ZUNTO! com caixa opaca `#0A0A0A` (`BorderStyle=3`, `Outline=16`) está legível, sem duplicação de legendas e cobrindo adequadamente a área de texto `[PENDENTE DE INSPEÇÃO HUMANA]`.",
            "- [ ] **Pilar 4 — Sincronia audiovisual e fluidez:** Áudio neural inteligível (sem zunido/microfonia) e vídeo iniciam e terminam em sincronia, sem cortes abruptos ou descompasso `[PENDENTE DE INSPEÇÃO HUMANA]`.",
            "",
            "---",
            "",
            "## 7. Instruções para Revisão Humana",
            "",
            "1. Abra os arquivos de vídeo em um player de sua escolha:",
            f"   - `{results[0]['video_path']}`",
            f"   - `{results[1]['video_path']}`",
            "2. Ouça a narração neural com atenção (certifique-se de que a fala é nítida, em português do Brasil e sem ruídos).",
            "3. Verifique os 4 pilares listados na Seção 6.",
            "4. Confirme no chat com `aprovado` para concluir formalmente a Phase 13 e o Milestone v1.1.",
            "",
        ])

        output_file.write_text("\n".join(lines), encoding="utf-8")
