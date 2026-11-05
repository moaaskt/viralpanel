import json
import shutil
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path


def probe_duration(media_path: Path) -> float:
    """Retorna a duração em segundos de um arquivo de áudio/vídeo usando ffprobe."""
    if not media_path.exists():
        return 0.0
    if shutil.which("ffprobe") is None:
        return 1.0
    proc = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(media_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(proc.stdout or "{}")
    return float(data.get("format", {}).get("duration", 0.0))


class BaseVoiceSynthesizer(ABC):
    @abstractmethod
    def synthesize(
        self,
        text: str,
        output_path: Path,
        speaker_wav: Path | None = None,
    ) -> tuple[Path, float]:
        """Sintetiza o texto em arquivo WAV e retorna (caminho, duracao_segundos)."""
        raise NotImplementedError


class XTTSVoiceSynthesizer(BaseVoiceSynthesizer):
    """Integração com Coqui XTTS v2 para clonagem de voz."""

    def __init__(
        self,
        model_name: str = "tts_models/multilingual/multi-dataset/xtts_v2",
        language: str = "pt",
        default_speaker_wav: Path | str | None = None,
    ):
        self.model_name = model_name
        self.language = language
        self.default_speaker_wav = Path(default_speaker_wav) if default_speaker_wav else None
        self._tts = None

    def _load(self):
        if self._tts is None:
            from TTS.api import TTS  # import tardio para dependência opcional pesada

            self._tts = TTS(self.model_name)
        return self._tts

    def synthesize(
        self,
        text: str,
        output_path: Path,
        speaker_wav: Path | None = None,
    ) -> tuple[Path, float]:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        ref_wav = speaker_wav or self.default_speaker_wav
        tts = self._load()
        kwargs: dict = {"text": text, "file_path": str(output_path), "language": self.language}
        if ref_wav and Path(ref_wav).exists():
            kwargs["speaker_wav"] = str(ref_wav)
        tts.tts_to_file(**kwargs)
        return output_path, probe_duration(output_path)


class MockVoiceSynthesizer(BaseVoiceSynthesizer):
    """Gera áudio WAV sintético via FFmpeg lavfi com duração proporcional às palavras."""

    def __init__(self, words_per_second: float = 3.0, min_duration: float = 1.5, max_duration: float = 15.0):
        self.words_per_second = words_per_second
        self.min_duration = min_duration
        self.max_duration = max_duration

    def estimate_duration(self, text: str) -> float:
        words = max(len(text.split()), 1)
        raw = words / max(self.words_per_second, 0.5)
        return round(min(max(raw, self.min_duration), self.max_duration), 2)

    def synthesize(
        self,
        text: str,
        output_path: Path,
        speaker_wav: Path | None = None,
    ) -> tuple[Path, float]:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        duration = self.estimate_duration(text)
        if shutil.which("ffmpeg"):
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    f"sine=frequency=320:duration={duration}",
                    "-ac",
                    "1",
                    "-ar",
                    "24000",
                    str(output_path),
                ],
                check=True,
                capture_output=True,
                timeout=60,
            )
            actual = probe_duration(output_path) or duration
            return output_path, round(actual, 2)

        output_path.write_bytes(b"RIFFMOCKWAV")
        return output_path, duration

