import logging
import shutil
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from viralpanel.branding import SafeZones9x16, ZuntoPalette
from viralpanel.config import get_settings
from viralpanel.studio.voice import probe_duration

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AvatarConfig:
    """Configuração geométrica e visual do avatar reaction circular ZUNTO!."""

    avatar_image_path: Path | str | None = None
    size: int = SafeZones9x16.AVATAR_SIZE
    crop_mode: Literal["circle_alpha", "native_rgba"] = "circle_alpha"
    border_color: str = ZuntoPalette.IMPACT_YELLOW
    border_width: int = 4
    overlay_x_expr: str = "W-w-54"
    overlay_y_expr: str = "H-h-320"
    enable_waveform: bool = True
    waveform_color: str = "#FACC15@0.85"


def ensure_default_avatar_image(avatar_path: Path | str | None = None) -> Path:
    """Garante a existência da imagem base de avatar em assets/, criando uma imagem dark moderna se necessário."""
    target = Path(avatar_path).resolve() if avatar_path else Path("assets/creator_avatar.png").resolve()
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
    """Gera vídeo do avatar (300x300) a partir de foto base com recorte circular em canal alfa e espectro reativo."""

    def __init__(
        self,
        width: int = SafeZones9x16.AVATAR_SIZE,
        height: int = SafeZones9x16.AVATAR_SIZE,
        default_avatar_image: Path | str | None = None,
        config: AvatarConfig | None = None,
    ):
        settings = get_settings()
        self.width = width
        self.height = height
        raw_avatar_img = (
            default_avatar_image
            or (config.avatar_image_path if config else None)
            or settings.avatar_image_path
            or "assets/creator_avatar.png"
        )
        self.default_avatar_image = Path(raw_avatar_img)
        if config is not None:
            self.config = config
            self.width = config.size
            self.height = config.size
        else:
            self.config = AvatarConfig(
                size=self.width,
                avatar_image_path=self.default_avatar_image,
            )

    def generate_avatar_video(
        self,
        audio_path: Path,
        output_path: Path,
        avatar_image_path: Path | None = None,
    ) -> tuple[Path, float]:
        audio_path = Path(audio_path).resolve()
        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        duration = max(probe_duration(audio_path), 1.5)
        raw_img = avatar_image_path or self.config.avatar_image_path or self.default_avatar_image
        img_path = ensure_default_avatar_image(raw_img)

        if shutil.which("ffmpeg") and audio_path.exists() and img_path.exists():
            size = self.config.size
            border_width = self.config.border_width
            r_outer = size / 2.0
            r_inner = r_outer - border_width
            cx = size / 2.0
            cy = size / 2.0

            # Decomposição RGB da cor da borda (#FACC15 -> R=250, G=204, B=21)
            border_color_clean = self.config.border_color.strip().lstrip("#")
            if len(border_color_clean) >= 6:
                r_val = int(border_color_clean[0:2], 16)
                g_val = int(border_color_clean[2:4], 16)
                b_val = int(border_color_clean[4:6], 16)
            else:
                r_val, g_val, b_val = 250, 204, 21

            showwaves_color = self.config.waveform_color
            if showwaves_color.startswith("#"):
                showwaves_color = f"0x{showwaves_color[1:]}"

            if self.config.enable_waveform:
                wave_filter = (
                    f"[1:a]showwaves=s={size}x80:mode=line:colors={showwaves_color}:rate=24,format=rgba[wave];"
                    f"[base][wave]overlay=x=0:y=H-h-20:shortest=1[composed];"
                )
            else:
                wave_filter = "[base]null[composed];"

            filter_complex = (
                f"[0:v]scale={size}:{size}:force_original_aspect_ratio=increase,"
                f"crop={size}:{size},format=rgba[base];"
                f"{wave_filter}"
                f"[composed]geq="
                f"r='if(gt(hypot(X-{cx},Y-{cy}),{r_outer + 0.5}),0,if(gt(hypot(X-{cx},Y-{cy}),{r_inner}),{r_val},r(X,Y)))':"
                f"g='if(gt(hypot(X-{cx},Y-{cy}),{r_outer + 0.5}),0,if(gt(hypot(X-{cx},Y-{cy}),{r_inner}),{g_val},g(X,Y)))':"
                f"b='if(gt(hypot(X-{cx},Y-{cy}),{r_outer + 0.5}),0,if(gt(hypot(X-{cx},Y-{cy}),{r_inner}),{b_val},b(X,Y)))':"
                f"a='clip(255*({r_outer + 0.5}-hypot(X-{cx},Y-{cy})), 0, 255)'[vout]"
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
                "png",
                "-pix_fmt",
                "rgba",
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

    def __init__(
        self,
        width: int = SafeZones9x16.AVATAR_SIZE,
        height: int = SafeZones9x16.AVATAR_SIZE,
    ):
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

