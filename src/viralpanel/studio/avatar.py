import logging
import shutil
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

from viralpanel.config import get_settings
from viralpanel.studio.voice import probe_duration

logger = logging.getLogger(__name__)


def ensure_default_avatar_image(avatar_path: Path | str | None = None) -> Path:
    """Garante a existência da imagem base de avatar em assets/, criando uma imagem dark moderna se necessário."""
    target = Path(avatar_path) if avatar_path else Path("assets/creator_avatar.png")
    if target.exists() and target.stat().st_size > 0:
        return target

    target.parent.mkdir(parents=True, exist_ok=True)
    if shutil.which("ffmpeg"):
        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=#0f172a:s=512x512:d=0.1",
                    "-vf",
                    (
                        "drawbox=x=96:y=96:w=320:h=320:color=#1e293b:t=fill,"
                        "drawbox=x=128:y=128:w=256:h=256:color=#334155:t=fill,"
                        "drawbox=x=192:y=160:w=128:h=128:color=#38bdf8:t=fill,"
                        "drawbox=x=160:y=310:w=192:h=90:color=#0284c7:t=fill"
                    ),
                    "-frames:v",
                    "1",
                    "-update",
                    "1",
                    str(target),
                ],
                check=True,
                capture_output=True,
                timeout=15,
            )
            if target.exists():
                return target
        except Exception as exc:
            logger.warning("Falha ao gerar imagem padrão de avatar com FFmpeg: %s", exc)

    # Fallback PNG mínimo válido (1x1 transparente ou bytes)
    target.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")
    return target


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


class AudioReactiveAvatarAnimator(BaseAvatarAnimator):
    """Gera vídeo do avatar (360x360) a partir de foto base com espectro de onda reativo ao áudio."""

    def __init__(
        self,
        width: int = 360,
        height: int = 360,
        default_avatar_image: Path | str | None = None,
    ):
        self.width = width
        self.height = height
        settings = get_settings()
        self.default_avatar_image = Path(default_avatar_image or settings.avatar_image_path or "assets/creator_avatar.png")

    def generate_avatar_video(
        self,
        audio_path: Path,
        output_path: Path,
        avatar_image_path: Path | None = None,
    ) -> tuple[Path, float]:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        duration = max(probe_duration(audio_path), 1.5)
        img_path = ensure_default_avatar_image(avatar_image_path or self.default_avatar_image)

        if shutil.which("ffmpeg") and audio_path.exists() and img_path.exists():
            filter_complex = (
                f"[0:v]scale={self.width}:{self.height}:force_original_aspect_ratio=increase,"
                f"crop={self.width}:{self.height},format=yuv420p[base_avatar];"
                f"[1:a]showwaves=s={self.width}x64:mode=line:colors=#38bdf8@0.85:rate=24,format=yuva420p[wave];"
                f"[base_avatar][wave]overlay=0:H-h-8:shortest=1[vout]"
            )
            cmd = [
                "ffmpeg",
                "-y",
                "-loop",
                "1",
                "-i",
                str(img_path),
                "-i",
                str(audio_path),
                "-filter_complex",
                filter_complex,
                "-map",
                "[vout]",
                "-map",
                "1:a",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-shortest",
                str(output_path),
            ]
            subprocess.run(cmd, check=True, capture_output=True, timeout=90)
            actual = probe_duration(output_path) or duration
            return output_path, round(actual, 2)

        output_path.write_bytes(b"MOCKAVATARMP4")
        return output_path, duration


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

