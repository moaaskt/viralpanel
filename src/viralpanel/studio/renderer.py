import json
import logging
import shutil
import subprocess
from pathlib import Path

from viralpanel.branding import SafeZones9x16
from viralpanel.studio.voice import probe_duration

logger = logging.getLogger(__name__)


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
        width: int = 1080,
        height: int = 1920,
        avatar_size: int = SafeZones9x16.AVATAR_SIZE,
        timeout_seconds: int = 300,
    ):
        self.width = width
        self.height = height
        self.avatar_size = avatar_size
        self.timeout_seconds = timeout_seconds

    def render(
        self,
        source_video_path: Path,
        avatar_video_path: Path,
        voice_audio_path: Path,
        ass_subtitle_path: Path,
        output_path: Path,
    ) -> tuple[Path, float]:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        duration = max(probe_duration(voice_audio_path), 1.5)

        if shutil.which("ffmpeg") is None:
            output_path.write_bytes(b"MOCKFINALMP4")
            return output_path, duration

        actual_source_path = source_video_path
        if not has_video_stream(source_video_path):
            logger.warning(
                "Arquivo source %s não contém stream de vídeo. Gerando fundo visual 9:16 de fallback...",
                source_video_path,
            )
            actual_source_path = source_video_path.parent / "source_visual_bg.mp4"
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    f"color=c=#0f172a:s={self.width}x{self.height}:r=24:d={duration}",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    str(actual_source_path),
                ],
                check=True,
                capture_output=True,
                timeout=30,
            )

        # Escapa o caminho do arquivo ASS para o filtro do FFmpeg
        escaped_ass = str(ass_subtitle_path.resolve()).replace("\\", "/").replace(":", "\\:")

        filter_complex = (
            f"[0:v]scale={self.width}:{self.height}:force_original_aspect_ratio=increase,"
            f"crop={self.width}:{self.height},setsar=1[bg];"
            f"[1:v]scale={self.avatar_size}:{self.avatar_size}:force_original_aspect_ratio=decrease[pip];"
            f"[bg][pip]overlay=W-w-{SafeZones9x16.AVATAR_MARGIN_RIGHT}:H-h-{SafeZones9x16.AVATAR_MARGIN_BOTTOM}:shortest=1[composed];"
            f"[composed]ass='{escaped_ass}'[vout]"
        )

        cmd = [
            "ffmpeg",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(actual_source_path),
            "-stream_loop",
            "-1",
            "-i",
            str(avatar_video_path),
            "-i",
            str(voice_audio_path),
            "-t",
            str(duration),
            "-filter_complex",
            filter_complex,
            "-map",
            "[vout]",
            "-map",
            "2:a",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            str(output_path),
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=self.timeout_seconds)
        except subprocess.CalledProcessError as exc:
            stderr_msg = exc.stderr.strip() if exc.stderr else "sem detalhes de stderr"
            logger.error("Falha na renderização de vídeo final FFmpeg: %s", stderr_msg)
            raise RuntimeError(f"Erro ao renderizar vídeo com FFmpeg: {stderr_msg}") from exc

        actual_duration = probe_duration(output_path) or duration
        return output_path, round(actual_duration, 2)

