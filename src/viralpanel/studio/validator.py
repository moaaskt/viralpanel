from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import json
import math
from pathlib import Path
import shutil
import subprocess
from typing import Any

from viralpanel.branding import SafeZones9x16


@dataclass(frozen=True)
class MediaStreamInfo:
    """Metadados estruturados de uma stream de mídia extraídos via FFprobe."""

    codec_name: str
    codec_type: str
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    pix_fmt: str | None = None
    duration: float | None = None
    sample_rate: int | None = None


@dataclass(frozen=True)
class ValidationResult:
    """Resultado consolidado da validação técnica de um arquivo de mídia."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PixelInspectionResult:
    """Resultado objetivo da inspeção de pixels em frame composto."""

    passed: bool
    details: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def parse_frame_rate(rate_str: str | None) -> float | None:
    """Interpreta valores racionais de frame rate do FFprobe (ex: '24/1', '24000/1001').

    Retorna None caso o valor seja ausente, '0/0', zero, negativo ou inválido.
    """
    if not rate_str or not isinstance(rate_str, str):
        return None
    cleaned = rate_str.strip()
    if not cleaned or cleaned in {"0/0", "0", "N/A"}:
        return None
    try:
        frac = Fraction(cleaned)
        if frac <= 0:
            return None
        return float(frac)
    except (ValueError, ZeroDivisionError):
        return None


def resolve_duration(stream_dict: dict[str, Any], format_dict: dict[str, Any]) -> float:
    """Resolve a duração da mídia com fallback documentado em cascata.

    Ordem de resolução:
    1. `stream_dict['duration']` se presente, numérico e > 0.
    2. `format_dict['duration']` se presente, numérico e > 0.
    3. Levanta `ValueError` explícito caso não seja possível determinar a duração
       (nunca aprova silenciosamente).
    """
    for candidate in (stream_dict.get("duration"), format_dict.get("duration")):
        if candidate is not None and str(candidate).strip() not in {"", "N/A", "none", "None"}:
            try:
                val = float(candidate)
                if math.isfinite(val) and val > 0:
                    return val
            except (ValueError, TypeError):
                continue

    raise ValueError("Duração não pôde ser determinada nem no stream nem no container format")


def _extract_stream_fps(stream_dict: dict[str, Any]) -> float | None:
    """Extrai FPS priorizando avg_frame_rate com fallback para r_frame_rate."""
    avg_fps = parse_frame_rate(stream_dict.get("avg_frame_rate"))
    r_fps = parse_frame_rate(stream_dict.get("r_frame_rate"))
    if avg_fps is not None:
        return avg_fps
    return r_fps


class MediaQualityValidator:
    """Validador técnico determinístico de mídia pós-renderização (QUAL-01)."""

    def __init__(self, timeout_seconds: int = 30):
        self.timeout_seconds = timeout_seconds

    def probe(self, file_path: Path | str) -> dict[str, Any]:
        """Executa ffprobe com saída JSON estruturada para format e streams."""
        resolved = Path(file_path).resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"Arquivo de mídia não encontrado: {resolved}")
        if resolved.stat().st_size == 0:
            raise ValueError(f"Arquivo de mídia vazio (0 bytes): {resolved}")
        if shutil.which("ffprobe") is None:
            raise RuntimeError("Executável ffprobe não encontrado no PATH do sistema")

        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                str(resolved),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=self.timeout_seconds,
        )
        data = json.loads(proc.stdout or "{}")
        if not isinstance(data, dict):
            raise ValueError("Saída JSON inválida retornada pelo ffprobe")
        return data

    def validate_rendered_video(
        self,
        video_path: Path | str,
        target_width: int = SafeZones9x16.WIDTH,
        target_height: int = SafeZones9x16.HEIGHT,
        target_fps: float = 24.0,
        fps_tolerance: float = 0.15,
        max_duration_diff_sec: float = 0.5,
    ) -> ValidationResult:
        """Valida especificações técnicas do vídeo final composto (1080x1920, 9:16, H.264/AAC, 24fps)."""
        errors: list[str] = []
        warnings: list[str] = []
        metrics: dict[str, Any] = {}

        try:
            probe_data = self.probe(video_path)
        except Exception as exc:
            return ValidationResult(
                is_valid=False,
                errors=[f"Falha ao executar probe no arquivo: {exc}"],
                warnings=warnings,
                metrics=metrics,
            )

        streams = probe_data.get("streams") or []
        format_dict = probe_data.get("format") or {}

        video_streams = [s for s in streams if s.get("codec_type") == "video"]
        audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

        if not video_streams:
            errors.append("Stream de vídeo ausente no container")
        if not audio_streams:
            errors.append("Stream de áudio ausente no container")

        if errors:
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings, metrics=metrics)

        v_stream = video_streams[0]
        a_stream = audio_streams[0]

        width = int(v_stream.get("width") or 0)
        height = int(v_stream.get("height") or 0)
        v_codec = str(v_stream.get("codec_name") or "").lower()
        pix_fmt = str(v_stream.get("pix_fmt") or "").lower()
        avg_fps = parse_frame_rate(v_stream.get("avg_frame_rate"))
        r_fps = parse_frame_rate(v_stream.get("r_frame_rate"))
        fps = avg_fps if avg_fps is not None else r_fps

        a_codec = str(a_stream.get("codec_name") or "").lower()
        try:
            sample_rate = int(a_stream.get("sample_rate") or 0)
        except (ValueError, TypeError):
            sample_rate = 0

        metrics.update(
            {
                "width": width,
                "height": height,
                "aspect_ratio": f"{width}:{height}",
                "video_codec": v_codec,
                "pix_fmt": pix_fmt,
                "fps": round(fps, 4) if fps is not None else None,
                "avg_frame_rate": v_stream.get("avg_frame_rate"),
                "r_frame_rate": v_stream.get("r_frame_rate"),
                "audio_codec": a_codec,
                "sample_rate": sample_rate,
                "format_name": format_dict.get("format_name"),
            }
        )

        # 1. Resolução e Aspect Ratio 9:16
        if width != target_width or height != target_height:
            errors.append(
                f"Dimensões inválidas: esperado {target_width}x{target_height} (9:16), obtido {width}x{height}"
            )
        elif width * 16 != height * 9:
            errors.append(f"Aspect ratio inválido: {width}x{height} não corresponde a 9:16")

        # 2. Codec de vídeo e pixel format
        if v_codec != "h264":
            errors.append(f"Codec de vídeo inválido: esperado 'h264', obtido '{v_codec}'")
        if pix_fmt != "yuv420p":
            errors.append(f"Formato de pixel inválido: esperado 'yuv420p', obtido '{pix_fmt}'")

        # 3. Frame rate racional (avg_frame_rate e r_frame_rate)
        if fps is None:
            errors.append(
                f"FPS não pôde ser interpretado (avg={v_stream.get('avg_frame_rate')!r}, r={v_stream.get('r_frame_rate')!r})"
            )
        else:
            if abs(fps - target_fps) > fps_tolerance:
                # Se avg_frame_rate divergir levemente em clipes curtos mas r_frame_rate for exato 24.0,
                # só aceita se avg_frame_rate estiver dentro de 1.0 fps E r_frame_rate == target_fps
                if r_fps is not None and abs(r_fps - target_fps) <= fps_tolerance and abs(fps - target_fps) <= 1.0:
                    warnings.append(
                        f"avg_frame_rate ({fps:.3f}) apresenta leve variação em clipe curto, mas r_frame_rate é {r_fps:.3f}"
                    )
                else:
                    errors.append(f"FPS fora da especificação: esperado {target_fps}±{fps_tolerance}, obtido {fps:.3f}")

        # 4. Codec de áudio e taxa de amostragem
        if a_codec != "aac":
            errors.append(f"Codec de áudio inválido: esperado 'aac', obtido '{a_codec}'")
        if sample_rate < 44100:
            errors.append(f"Sample rate de áudio insuficiente: esperado >= 44100Hz, obtido {sample_rate}Hz")

        # 5. Duração com fallback documentado (sem aprovação silenciosa)
        v_dur: float | None = None
        a_dur: float | None = None
        try:
            v_dur = resolve_duration(v_stream, format_dict)
            metrics["video_duration"] = round(v_dur, 3)
        except ValueError as exc:
            errors.append(f"Falha na duração de vídeo: {exc}")

        try:
            a_dur = resolve_duration(a_stream, format_dict)
            metrics["audio_duration"] = round(a_dur, 3)
        except ValueError as exc:
            errors.append(f"Falha na duração de áudio: {exc}")

        if v_dur is not None and a_dur is not None:
            diff = abs(v_dur - a_dur)
            metrics["duration_diff"] = round(diff, 3)
            if diff > max_duration_diff_sec:
                errors.append(
                    f"Divergência excessiva de duração entre vídeo ({v_dur:.2f}s) e áudio ({a_dur:.2f}s): diff={diff:.2f}s > {max_duration_diff_sec:.2f}s"
                )

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            metrics=metrics,
        )

    def validate_avatar_asset(
        self,
        avatar_path: Path | str,
        expected_size: int = SafeZones9x16.AVATAR_SIZE,
    ) -> ValidationResult:
        """Audita o asset intermediário de avatar gerado pela Phase 11 (codec png, pix_fmt rgba)."""
        errors: list[str] = []
        warnings: list[str] = []
        metrics: dict[str, Any] = {}

        try:
            probe_data = self.probe(avatar_path)
        except Exception as exc:
            return ValidationResult(
                is_valid=False,
                errors=[f"Falha ao executar probe no asset de avatar: {exc}"],
                warnings=warnings,
                metrics=metrics,
            )

        streams = probe_data.get("streams") or []
        format_dict = probe_data.get("format") or {}
        video_streams = [s for s in streams if s.get("codec_type") == "video"]

        if not video_streams:
            return ValidationResult(
                is_valid=False,
                errors=["Stream de vídeo ausente no asset de avatar"],
                warnings=warnings,
                metrics=metrics,
            )

        v_stream = video_streams[0]
        v_codec = str(v_stream.get("codec_name") or "").lower()
        pix_fmt = str(v_stream.get("pix_fmt") or "").lower()
        width = int(v_stream.get("width") or 0)
        height = int(v_stream.get("height") or 0)

        metrics.update(
            {
                "width": width,
                "height": height,
                "video_codec": v_codec,
                "pix_fmt": pix_fmt,
            }
        )

        if v_codec != "png":
            errors.append(f"Codec do asset de avatar inválido: esperado 'png' (Phase 11), obtido '{v_codec}'")
        if pix_fmt != "rgba":
            errors.append(f"Pixel format do avatar sem canal alfa: esperado 'rgba', obtido '{pix_fmt}'")
        if width != expected_size or height != expected_size:
            errors.append(f"Dimensões do avatar inválidas: esperado {expected_size}x{expected_size}, obtido {width}x{height}")

        try:
            dur = resolve_duration(v_stream, format_dict)
            metrics["duration"] = round(dur, 3)
        except ValueError as exc:
            errors.append(f"Duração do avatar indeterminável: {exc}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            metrics=metrics,
        )

    def inspect_composed_avatar_transparency(
        self,
        video_path: Path | str,
        expected_bg_rgb: tuple[int, int, int] = (15, 23, 42),
        timestamp_sec: float = 0.5,
        tolerance: int = 18,
    ) -> PixelInspectionResult:
        """Inspeciona os pixels de um frame do vídeo final composto (1080x1920) para comprovar:

        1. Que toda a região externa ao círculo do avatar dentro da sua bounding box
           (4 cantos de linha de base + malha distribuída de pontos em múltiplos ângulos e raios)
           preserva o fundo esperado (sem caixa opaca branca/preta nem defeitos parciais localizados).
        2. Que o contorno circular do avatar apresenta o amarelo oficial ZUNTO! (#FACC15).

        Critério objetivo de transparência externa:
        - Bounding box do avatar em 1080x1920: X in [726, 1026], Y in [1300, 1600],
          centro (cx=876, cy=1450), raio=150.
        - Tolerância por canal / distância: cada ponto amostrado externo ao círculo (hypot >= 156)
          deve ter diferença máxima por canal <= `tolerance` em relação a `expected_bg_rgb`.
        """
        resolved = Path(video_path).resolve()
        if not resolved.exists():
            return PixelInspectionResult(
                passed=False,
                errors=[f"Arquivo de vídeo não encontrado: {resolved}"],
            )
        if shutil.which("ffmpeg") is None:
            return PixelInspectionResult(
                passed=False,
                errors=["Executável ffmpeg não encontrado no PATH"],
            )

        width = SafeZones9x16.WIDTH
        height = SafeZones9x16.HEIGHT
        expected_bytes = width * height * 3

        proc = subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-ss",
                str(timestamp_sec),
                "-i",
                str(resolved),
                "-frames:v",
                "1",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgb24",
                "pipe:1",
            ],
            capture_output=True,
            check=True,
            timeout=self.timeout_seconds,
        )
        raw = proc.stdout
        if len(raw) < expected_bytes:
            return PixelInspectionResult(
                passed=False,
                errors=[f"Frame extraído incompleto: esperado {expected_bytes} bytes, obtido {len(raw)}"],
            )

        def get_rgb(x: int, y: int) -> tuple[int, int, int]:
            idx = (y * width + x) * 3
            return raw[idx], raw[idx + 1], raw[idx + 2]

        box_x0 = width - SafeZones9x16.AVATAR_SIZE - SafeZones9x16.AVATAR_MARGIN_RIGHT  # 726
        box_y0 = height - SafeZones9x16.AVATAR_SIZE - SafeZones9x16.AVATAR_MARGIN_BOTTOM  # 1300
        box_x1 = box_x0 + SafeZones9x16.AVATAR_SIZE  # 1026
        box_y1 = box_y0 + SafeZones9x16.AVATAR_SIZE  # 1600
        cx = box_x0 + SafeZones9x16.AVATAR_SIZE // 2  # 876
        cy = box_y0 + SafeZones9x16.AVATAR_SIZE // 2  # 1450
        radius = SafeZones9x16.AVATAR_SIZE / 2.0  # 150.0

        # 1. Os 4 cantos obrigatórios de linha de base (dentro da bounding box, fora do círculo)
        corner_points: dict[str, tuple[int, int]] = {
            "top_left": (box_x0 + 9, box_y0 + 10),        # (735, 1310)
            "top_right": (box_x1 - 11, box_y0 + 10),      # (1015, 1310)
            "bottom_left": (box_x0 + 9, box_y1 - 10),     # (735, 1590)
            "bottom_right": (box_x1 - 11, box_y1 - 10),   # (1015, 1590)
        }

        # 2. Malha distribuída por toda a região externa ao círculo dentro da bounding box
        # (hypot >= radius + 5.0 para evitar a zona de anti-aliasing da borda e subsampling 4:2:0)
        distributed_points: list[tuple[int, int]] = []
        for y in range(box_y0 + 3, box_y1 - 2, 12):
            for x in range(box_x0 + 3, box_x1 - 2, 12):
                dist = math.hypot(x - cx, y - cy)
                if dist >= radius + 5.0:
                    distributed_points.append((x, y))

        errors: list[str] = []
        corner_samples: dict[str, tuple[int, int, int]] = {}
        failed_distributed: list[dict[str, Any]] = []

        exp_r, exp_g, exp_b = expected_bg_rgb

        def _matches_bg(rgb: tuple[int, int, int]) -> bool:
            r, g, b = rgb
            return (
                abs(r - exp_r) <= tolerance
                and abs(g - exp_g) <= tolerance
                and abs(b - exp_b) <= tolerance
            )

        for label, (px, py) in corner_points.items():
            rgb = get_rgb(px, py)
            corner_samples[label] = rgb
            if not _matches_bg(rgb):
                errors.append(
                    f"Canto '{label}' ({px}, {py}) divergiu do fundo esperado {expected_bg_rgb}: obtido RGB={rgb} (tolerância={tolerance})"
                )

        for px, py in distributed_points:
            rgb = get_rgb(px, py)
            if not _matches_bg(rgb):
                failed_distributed.append({"coord": (px, py), "rgb": rgb})

        if failed_distributed:
            sample_Preview = failed_distributed[:5]
            errors.append(
                f"Detectada opacidade/defeito localizado em {len(failed_distributed)} ponto(s) distribuído(s) na região externa ao círculo. Exemplos: {sample_Preview}"
            )

        # 3. Verificação da borda amarela ZUNTO! (#FACC15 -> R=250, G=204, B=21)
        # Amostra raios 146..149 no arco superior/lateral (livre do showwaves inferior)
        border_angles_deg = [-90, -45, 0, -135, 180]
        border_samples: dict[str, tuple[int, int, int]] = {}
        yellow_detected_count = 0

        for angle_deg in border_angles_deg:
            rad = math.radians(angle_deg)
            best_rgb = (0, 0, 0)
            for r_step in (146.5, 147.5, 148.0, 148.5, 149.0):
                bx = int(round(cx + r_step * math.cos(rad)))
                by = int(round(cy + r_step * math.sin(rad)))
                cand_rgb = get_rgb(bx, by)
                if cand_rgb[0] + cand_rgb[1] > best_rgb[0] + best_rgb[1]:
                    best_rgb = cand_rgb
            border_samples[f"angle_{angle_deg}"] = best_rgb
            # Verifica assinatura cromática do amarelo #FACC15 (R alto, G alto, B baixo)
            if best_rgb[0] >= 160 and best_rgb[1] >= 125 and best_rgb[2] <= 110 and (best_rgb[0] - best_rgb[2]) >= 80:
                yellow_detected_count += 1

        if yellow_detected_count < 3:
            errors.append(
                f"Contorno amarelo ZUNTO! (#FACC15) não detectado na borda circular do avatar: amostras={border_samples}"
            )

        details = {
            "bounding_box": {"x0": box_x0, "y0": box_y0, "x1": box_x1, "y1": box_y1},
            "center": (cx, cy),
            "radius": radius,
            "expected_bg_rgb": expected_bg_rgb,
            "tolerance": tolerance,
            "corner_samples": corner_samples,
            "distributed_points_checked": len(distributed_points),
            "distributed_points_failed": len(failed_distributed),
            "border_samples": border_samples,
            "yellow_border_rays_confirmed": f"{yellow_detected_count}/{len(border_angles_deg)}",
        }

        return PixelInspectionResult(
            passed=len(errors) == 0,
            details=details,
            errors=errors,
        )
