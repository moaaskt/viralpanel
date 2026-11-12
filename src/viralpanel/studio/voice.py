import asyncio
import json
import logging
import shutil
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

from viralpanel.config import get_settings

logger = logging.getLogger(__name__)


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


class EdgeTTSVoiceSynthesizer(BaseVoiceSynthesizer):
    """Síntese de voz neural ultra-realista pt-BR via edge-tts com normalização loudnorm."""

    def __init__(self, voice: str | None = None, rate: str | None = None):
        settings = get_settings()
        self.voice = voice or settings.edge_tts_voice
        self.rate = rate or settings.edge_tts_rate

    def synthesize(
        self,
        text: str,
        output_path: Path,
        speaker_wav: Path | None = None,
    ) -> tuple[Path, float]:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temp_mp3 = output_path.with_suffix(".edge.temp.mp3")
        try:
            import edge_tts

            async def _run():
                communicate = edge_tts.Communicate(text, self.voice, rate=self.rate)
                await communicate.save(str(temp_mp3))

            asyncio.run(_run())

            if shutil.which("ffmpeg") and temp_mp3.exists():
                subprocess.run(
                    [
                        "ffmpeg",
                        "-y",
                        "-i",
                        str(temp_mp3),
                        "-af",
                        "loudnorm=I=-16:TP=-1.5:LRA=11",
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
            elif temp_mp3.exists():
                shutil.copy(temp_mp3, output_path)

            duration = probe_duration(output_path)
            return output_path, round(duration, 2)
        finally:
            if temp_mp3.exists():
                temp_mp3.unlink(missing_ok=True)


class FallbackVoiceSynthesizer(BaseVoiceSynthesizer):
    """Cadeia de sintetizadores: XTTS v2 (se configurado e com voz de referência) -> Edge-TTS pt-BR -> Mock."""

    def __init__(self, synthesizers: list[BaseVoiceSynthesizer] | None = None):
        if synthesizers is not None:
            self.synthesizers = synthesizers
        else:
            settings = get_settings()
            self.synthesizers = []

            # 1. XTTS v2 se configurado e com áudio de referência do criador presente
            if settings.tts_provider == "xtts" and settings.speaker_wav_path and Path(settings.speaker_wav_path).exists():
                try:
                    self.synthesizers.append(XTTSVoiceSynthesizer(default_speaker_wav=settings.speaker_wav_path))
                except Exception as e:
                    logger.warning("Falha ao inicializar XTTS: %s", e)

            # 2. Edge-TTS Neural pt-BR (padrão principal de alta fidelidade)
            try:
                self.synthesizers.append(EdgeTTSVoiceSynthesizer(voice=settings.edge_tts_voice, rate=settings.edge_tts_rate))
            except Exception as e:
                logger.warning("Falha ao inicializar Edge-TTS: %s", e)

            # 3. Mock como salvaguarda
            self.synthesizers.append(MockVoiceSynthesizer())

    def synthesize(
        self,
        text: str,
        output_path: Path,
        speaker_wav: Path | None = None,
    ) -> tuple[Path, float]:
        errors = []
        for syn in self.synthesizers:
            name = syn.__class__.__name__
            try:
                logger.info("Tentando síntese de voz com %s...", name)
                out, dur = syn.synthesize(text, output_path, speaker_wav=speaker_wav)
                logger.info("Voz sintetizada com sucesso via %s (duração: %.2fs)", name, dur)
                return out, dur
            except Exception as exc:
                logger.warning("Falha no sintetizador %s: %s. Tentando próximo...", name, exc)
                errors.append(f"{name}: {exc}")

        raise RuntimeError(f"Todos os sintetizadores de voz falharam: {'; '.join(errors)}")


