import json
import shutil
import subprocess
from pathlib import Path

from viralpanel.studio.voice import probe_duration


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


class ReactionVideoRenderer:
    """Compõe vídeo vertical 9:16 (1080x1920) com vídeo base, avatar em PIP e legendas ASS."""

    def __init__(
        self,
        width: int = 1080,
        height: int = 1920,
        avatar_size: int = 340,
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

        # Escapa o caminho do arquivo ASS para o filtro do FFmpeg
        escaped_ass = str(ass_subtitle_path.resolve()).replace("\\", "/").replace(":", "\\:")

        filter_complex = (
            f"[0:v]scale={self.width}:{self.height}:force_original_aspect_ratio=increase,"
            f"crop={self.width}:{self.height},setsar=1[bg];"
            f"[1:v]scale={self.avatar_size}:{self.avatar_size}:force_original_aspect_ratio=decrease,"
            f"pad={self.avatar_size + 12}:{self.avatar_size + 12}:6:6:color=white[pip];"
            f"[bg][pip]overlay=W-w-48:H-h-120:shortest=1[composed];"
            f"[composed]ass='{escaped_ass}'[vout]"
        )

        cmd = [
            "ffmpeg",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(source_video_path),
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
            str(output_path),
        ]

        subprocess.run(cmd, check=True, capture_output=True, timeout=self.timeout_seconds)
        actual_duration = probe_duration(output_path) or duration
        return output_path, round(actual_duration, 2)

