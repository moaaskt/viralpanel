import logging
import os
import shutil
import subprocess
from pathlib import Path

from viralpanel.config import get_settings
from viralpanel.storage import StorageManager

logger = logging.getLogger(__name__)


class MediaDownloader:
    """Baixa o vídeo de referência (yt-dlp) com flags robustas e extrai áudio limpo (FFmpeg)."""

    def __init__(
        self,
        storage: StorageManager | None = None,
        timeout_seconds: int = 300,
        cookies_path: str | None = None,
    ):
        self.storage = storage or StorageManager()
        self.timeout_seconds = timeout_seconds
        settings = get_settings()
        self.cookies_path = cookies_path or settings.tiktok_cookies_path

    def source_dir(self, run_id: str) -> Path:
        d = self.storage._safe(self.storage.get_run_dir(run_id).parent / "source")
        d.mkdir(parents=True, exist_ok=True)
        return d

    def download_video(self, run_id: str, url: str) -> Path:
        if shutil.which("yt-dlp") is None:
            raise RuntimeError("yt-dlp não encontrado no PATH (pip install yt-dlp)")

        target = self.source_dir(run_id) / "source.mp4"
        cmd = [
            "yt-dlp",
            "-f", "mp4/best[ext=mp4]/best",
            "-o", str(target),
            "--no-playlist",
            "--geo-bypass",
            "--user-agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        ]

        if self.cookies_path and os.path.exists(self.cookies_path):
            cmd.extend(["--cookies", str(self.cookies_path)])

        cmd.append(url)

        try:
            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except subprocess.CalledProcessError as exc:
            stderr_msg = exc.stderr.strip() if exc.stderr else "sem detalhes de stderr"
            logger.error("Falha ao baixar vídeo com yt-dlp para %s: %s", url, stderr_msg)
            raise RuntimeError(f"Erro ao baixar vídeo com yt-dlp ({url}): {stderr_msg}") from exc
        except subprocess.TimeoutExpired as exc:
            logger.error("Timeout ao baixar vídeo com yt-dlp para %s após %ss", url, self.timeout_seconds)
            raise RuntimeError(f"Timeout ao baixar vídeo ({url}) após {self.timeout_seconds}s") from exc

        if not target.exists() or target.stat().st_size == 0:
            raise RuntimeError(f"Download concluído mas arquivo de vídeo não encontrado ou vazio: {target}")

        return target

    def extract_audio(self, video_path: Path, output_audio_path: Path | None = None) -> Path:
        if shutil.which("ffmpeg") is None:
            raise RuntimeError("ffmpeg não encontrado no PATH")

        out = output_audio_path or video_path.with_name("audio.wav")
        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(video_path),
            "-vn",
            "-ac", "1",
            "-ar", "16000",
            "-af", "highpass=f=80,lowpass=f=8000",
            str(out),
        ]
        try:
            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except subprocess.CalledProcessError as exc:
            stderr_msg = exc.stderr.strip() if exc.stderr else "sem detalhes de stderr"
            logger.error("Falha ao extrair áudio com ffmpeg de %s: %s", video_path, stderr_msg)
            raise RuntimeError(f"Erro ao extrair áudio com ffmpeg: {stderr_msg}") from exc

        return out

    def fetch(self, run_id: str, url: str) -> tuple[Path, Path]:
        video = self.download_video(run_id, url)
        audio = self.extract_audio(video)
        return video, audio


class MockMediaDownloader(MediaDownloader):
    """Gera um vídeo/áudio sintético local (FFmpeg lavfi) sem acesso à rede."""

    def download_video(self, run_id: str, url: str) -> Path:
        target = self.source_dir(run_id) / "source.mp4"
        if shutil.which("ffmpeg"):
            subprocess.run(
                [
                    "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=gray:s=320x568:d=2",
                    "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
                    "-shortest", "-c:v", "libx264", "-c:a", "aac", str(target),
                ],
                check=True,
                capture_output=True,
                timeout=60,
            )
        else:
            target.write_bytes(b"MOCKVIDEO")
        return target

    def extract_audio(self, video_path: Path, output_audio_path: Path | None = None) -> Path:
        if shutil.which("ffmpeg") and video_path.read_bytes()[:9] != b"MOCKVIDEO":
            return super().extract_audio(video_path, output_audio_path)
        out = output_audio_path or video_path.with_name("audio.wav")
        out.write_bytes(b"MOCKAUDIO")
        return out
