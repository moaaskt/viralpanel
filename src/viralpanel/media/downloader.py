import shutil
import subprocess
from pathlib import Path

from viralpanel.storage import StorageManager


class MediaDownloader:
    """Baixa o vídeo de referência (yt-dlp) e extrai áudio limpo (FFmpeg)."""

    def __init__(self, storage: StorageManager | None = None, timeout_seconds: int = 300):
        self.storage = storage or StorageManager()
        self.timeout_seconds = timeout_seconds

    def source_dir(self, run_id: str) -> Path:
        d = self.storage._safe(self.storage.get_run_dir(run_id).parent / "source")
        d.mkdir(parents=True, exist_ok=True)
        return d

    def download_video(self, run_id: str, url: str) -> Path:
        if shutil.which("yt-dlp") is None:
            raise RuntimeError("yt-dlp não encontrado no PATH (pip install yt-dlp)")
        target = self.source_dir(run_id) / "source.mp4"
        subprocess.run(
            ["yt-dlp", "-f", "mp4/best", "-o", str(target), "--no-playlist", url],
            check=True, capture_output=True, timeout=self.timeout_seconds,
        )
        return target

    def extract_audio(self, video_path: Path, output_audio_path: Path | None = None) -> Path:
        out = output_audio_path or video_path.with_name("audio.wav")
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(video_path), "-vn", "-ac", "1", "-ar", "16000",
             "-af", "highpass=f=80,lowpass=f=8000", str(out)],
            check=True, capture_output=True, timeout=self.timeout_seconds,
        )
        return out

    def fetch(self, run_id: str, url: str) -> tuple[Path, Path]:
        video = self.download_video(run_id, url)
        return video, self.extract_audio(video)


class MockMediaDownloader(MediaDownloader):
    """Gera um vídeo/áudio sintético local (FFmpeg lavfi) sem acesso à rede."""

    def download_video(self, run_id: str, url: str) -> Path:
        target = self.source_dir(run_id) / "source.mp4"
        if shutil.which("ffmpeg"):
            subprocess.run(
                ["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=gray:s=320x568:d=2",
                 "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
                 "-shortest", "-c:v", "libx264", "-c:a", "aac", str(target)],
                check=True, capture_output=True, timeout=60,
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

