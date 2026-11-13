from __future__ import annotations

from dataclasses import dataclass, field
import json
import logging
from pathlib import Path
import shutil
import subprocess
from typing import TYPE_CHECKING
import uuid

from viralpanel.branding import SafeZones9x16
from viralpanel.studio.voice import probe_duration

if TYPE_CHECKING:
    from viralpanel.studio.avatar import AvatarConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReactionCompositionSpec:
    """Especificações técnicas da composição FFmpeg."""

    target_width: int = SafeZones9x16.WIDTH
    target_height: int = SafeZones9x16.HEIGHT
    fps: int = 24
    video_codec: str = "libx264"
    preset: str = "veryfast"
    crf: int = 20
    pix_fmt: str = "yuv420p"
    audio_codec: str = "aac"
    audio_bitrate: str = "192k"
    single_pass: bool = True
    timeout_seconds: int = 180


@dataclass(frozen=True)
class StudioRenderRequest:
    """Insumos estruturados para renderização de vídeo reaction."""

    run_id: str | uuid.UUID
    source_video_path: Path
    avatar_video_path: Path
    voice_audio_path: Path
    ass_subtitle_path: Path
    output_path: Path
    voice_duration: float | None = None
    avatar_config: AvatarConfig | None = None
    composition: ReactionCompositionSpec = field(default_factory=ReactionCompositionSpec)

    def __post_init__(self) -> None:
        for field_name in (
            "source_video_path",
            "avatar_video_path",
            "voice_audio_path",
            "ass_subtitle_path",
            "output_path",
        ):
            val = getattr(self, field_name)
            if val is not None and not isinstance(val, Path):
                object.__setattr__(self, field_name, Path(val))


def probe_video_dimensions(video_path: Path) -> tuple[int, int]:
    """Retorna (width, height) do vídeo via ffprobe."""
    if not video_path.exists() or shutil.which("ffprobe") is None:
        return (1080, 1920)
    proc = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "json",
            str(video_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(proc.stdout or "{}")
    streams = data.get("streams") or [{}]
    return int(streams[0].get("width", 1080)), int(streams[0].get("height", 1920))


def has_video_stream(media_path: Path) -> bool:
    """Verifica se o arquivo contém ao menos uma stream de vídeo."""
    if not media_path.exists() or shutil.which("ffprobe") is None:
        return False
    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v",
                "-show_entries",
                "stream=codec_type",
                "-of",
                "csv=p=0",
                str(media_path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return "video" in proc.stdout.lower()
    except Exception:
        return False


class ReactionVideoRenderer:
    """Compõe vídeo vertical 9:16 (1080x1920) com vídeo base, avatar em PIP e legendas ASS."""

    def __init__(
        self,
        width: int = SafeZones9x16.WIDTH,
        height: int = SafeZones9x16.HEIGHT,
        avatar_size: int = SafeZones9x16.AVATAR_SIZE,
        preset: str = "veryfast",
        crf: int = 20,
        timeout_seconds: int = 180,
    ):
        self.width = width
        self.height = height
        self.avatar_size = avatar_size
        self.preset = preset
        self.crf = crf
        self.timeout_seconds = timeout_seconds

    def render_from_request(self, request: StudioRenderRequest) -> tuple[Path, float]:
        """Executa renderização FFmpeg em passagem única a partir de StudioRenderRequest."""
        request.output_path.parent.mkdir(parents=True, exist_ok=True)
        duration = (
            max(request.voice_duration, 1.5)
            if request.voice_duration and request.voice_duration > 0
            else max(probe_duration(request.voice_audio_path), 1.5)
        )

        if shutil.which("ffmpeg") is None:
            request.output_path.write_bytes(b"MOCKFINALMP4")
            return request.output_path, duration

        composition = request.composition

        if has_video_stream(request.source_video_path):
            source_inputs = ["-stream_loop", "-1", "-i", str(request.source_video_path)]
        else:
            logger.info(
                "Source %s sem stream de vídeo. Injetando lavfi inline 9:16 diretamente em [0:v].",
                request.source_video_path,
            )
            source_inputs = [
                "-f",
                "lavfi",
                "-i",
                f"color=c=#0f172a:s={composition.target_width}x{composition.target_height}:r={composition.fps}:d={duration}",
            ]

        # Escapa o caminho do arquivo ASS para o filtro do FFmpeg
        escaped_ass = str(request.ass_subtitle_path.resolve()).replace("\\", "/").replace(":", "\\:")
        avatar_size = request.avatar_config.size if request.avatar_config else self.avatar_size

        filter_complex = (
            f"[0:v]scale={composition.target_width}:{composition.target_height}:force_original_aspect_ratio=increase,"
            f"crop={composition.target_width}:{composition.target_height},setsar=1[bg];"
            f"[1:v]scale={avatar_size}:{avatar_size}:force_original_aspect_ratio=decrease[pip];"
            f"[bg][pip]overlay=W-w-{SafeZones9x16.AVATAR_MARGIN_RIGHT}:H-h-{SafeZones9x16.AVATAR_MARGIN_BOTTOM}:shortest=1[composed];"
            f"[composed]ass='{escaped_ass}'[vout]"
        )

        cmd = [
            "ffmpeg",
            "-y",
            "-threads",
            "1",
            "-filter_complex_threads",
            "1",
            *source_inputs,
            "-stream_loop",
            "-1",
            "-i",
            str(request.avatar_video_path),
            "-i",
            str(request.voice_audio_path),
            "-t",
            str(duration),
            "-filter_complex",
            filter_complex,
            "-map",
            "[vout]",
            "-map",
            "2:a",
            "-c:v",
            composition.video_codec,
            "-preset",
            composition.preset,
            "-crf",
            str(composition.crf),
            "-threads",
            "2",
            "-x264-params",
            "threads=2:lookahead_threads=0",
            "-pix_fmt",
            composition.pix_fmt,
            "-r",
            str(composition.fps),
            "-c:a",
            composition.audio_codec,
            "-b:a",
            composition.audio_bitrate,
            "-ar",
            "44100",
            "-shortest",
            str(request.output_path),
        ]

        try:
            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=composition.timeout_seconds,
            )
        except subprocess.CalledProcessError as exc:
            stderr_msg = exc.stderr.strip() if exc.stderr else "sem detalhes de stderr"
            logger.error("Falha na renderização de vídeo final FFmpeg: %s", stderr_msg)
            raise RuntimeError(f"Erro ao renderizar vídeo com FFmpeg: {stderr_msg}") from exc

        actual_duration = probe_duration(request.output_path) or duration
        return request.output_path, round(actual_duration, 2)

    def render(
        self,
        source_video_path: Path | StudioRenderRequest,
        avatar_video_path: Path | None = None,
        voice_audio_path: Path | None = None,
        ass_subtitle_path: Path | None = None,
        output_path: Path | None = None,
        **kwargs,
    ) -> tuple[Path, float]:
        if isinstance(source_video_path, StudioRenderRequest):
            return self.render_from_request(source_video_path)

        if (
            avatar_video_path is None
            or voice_audio_path is None
            or ass_subtitle_path is None
            or output_path is None
        ):
            raise ValueError(
                "avatar_video_path, voice_audio_path, ass_subtitle_path e output_path são obrigatórios quando StudioRenderRequest não é utilizado."
            )

        run_id = kwargs.get("run_id", "legacy_run")
        voice_duration = kwargs.get("voice_duration")
        avatar_config = kwargs.get("avatar_config")
        composition = kwargs.get(
            "composition",
            ReactionCompositionSpec(
                target_width=self.width,
                target_height=self.height,
                preset=self.preset,
                crf=self.crf,
                timeout_seconds=self.timeout_seconds,
            ),
        )

        request = StudioRenderRequest(
            run_id=run_id,
            source_video_path=source_video_path,
            avatar_video_path=avatar_video_path,
            voice_audio_path=voice_audio_path,
            ass_subtitle_path=ass_subtitle_path,
            output_path=output_path,
            voice_duration=voice_duration,
            avatar_config=avatar_config,
            composition=composition,
        )
        return self.render_from_request(request)

