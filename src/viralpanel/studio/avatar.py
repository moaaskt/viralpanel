import shutil
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

from viralpanel.studio.voice import probe_duration


class BaseAvatarAnimator(ABC):
    @abstractmethod
    def generate_avatar_video(
        self,
        audio_path: Path,
        output_path: Path,
        avatar_image_path: Path | None = None,
    ) -> tuple[Path, float]:
        """Gera vídeo do avatar sincronizado com o áudio narrado e retorna (caminho, duracao_segundos)."""
        raise NotImplementedError


class MockAvatarAnimator(BaseAvatarAnimator):
    """Gera vídeo sintético do avatar falante sincronizado com a duração exata do áudio de narração."""

    def __init__(self, width: int = 360, height: int = 360):
        self.width = width
        self.height = height

    def generate_avatar_video(
        self,
        audio_path: Path,
        output_path: Path,
        avatar_image_path: Path | None = None,
    ) -> tuple[Path, float]:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        duration = max(probe_duration(audio_path), 1.5)

        if shutil.which("ffmpeg") and audio_path.exists():
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    f"color=c=#1e293b:s={self.width}x{self.height}:r=24:d={duration}",
                    "-i",
                    str(audio_path),
                    "-shortest",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    str(output_path),
                ],
                check=True,
                capture_output=True,
                timeout=90,
            )
            actual = probe_duration(output_path) or duration
            return output_path, round(actual, 2)

        output_path.write_bytes(b"MOCKAVATARMP4")
        return output_path, duration
