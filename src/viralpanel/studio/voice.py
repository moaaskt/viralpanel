import asyncio
import hashlib
import json
import logging
import shutil
import subprocess
import wave
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from viralpanel.config import get_settings

logger = logging.getLogger(__name__)


def compute_file_sha256(path: Path) -> str:
    """Calcula o hash SHA-256 de um arquivo em blocos de 64KB."""
    digest = hashlib.sha256()
    with open(path, "rb") as file_handle:
        while chunk := file_handle.read(65536):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_sha256(value: str | None) -> str | None:
    if value is None or not isinstance(value, str):
        return None
    cleaned = value.strip()
    if cleaned.startswith("sha256:"):
        cleaned = cleaned[len("sha256:") :]
    return cleaned.lower()


def load_and_validate_word_timestamps(
    sidecar_path: Path,
    expected_text: str | None = None,
    expected_duration: float | None = None,
    expected_audio_path: Path | None = None,
) -> list[dict] | None:
    """Valida e carrega timestamps de fala de um arquivo sidecar .words.json.

    Verifica integridade estrutural, text_hash, audio_hash e coerência de duração.
    Retorna None com log de aviso se qualquer validação falhar, acionando fallback proporcional.
    """
    sidecar = Path(sidecar_path)
    if not sidecar.is_file():
        return None

    try:
        raw_text = sidecar.read_text(encoding="utf-8")
        if not raw_text.strip():
            logger.warning("Sidecar %s está vazio. Acionando fallback proporcional.", sidecar)
            return None
        data = json.loads(raw_text)
    except Exception as exc:
        logger.warning("Erro ao ler sidecar %s: %s. Acionando fallback proporcional.", sidecar, exc)
        return None

    if isinstance(data, list):
        timestamps = data
        stored_duration = None
        stored_text_hash = None
        stored_audio_hash = None
    elif isinstance(data, dict):
        timestamps = data.get("timestamps")
        stored_duration = data.get("audio_duration_sec")
        stored_text_hash = _normalize_sha256(data.get("text_hash"))
        stored_audio_hash = _normalize_sha256(data.get("audio_hash"))
    else:
        logger.warning("Sidecar %s possui formato JSON inválido. Acionando fallback proporcional.", sidecar)
        return None

    if not isinstance(timestamps, list) or len(timestamps) == 0:
        logger.warning("Sidecar %s possui lista de timestamps vazia ou inválida. Acionando fallback proporcional.", sidecar)
        return None

    if expected_text is not None and stored_text_hash is not None:
        expected_text_hash = hashlib.sha256(expected_text.encode("utf-8")).hexdigest().lower()
        if stored_text_hash != expected_text_hash:
            logger.warning(
                "Sidecar %s possui text_hash divergente do roteiro esperado. "
                "Descartando sidecar e acionando fallback proporcional.",
                sidecar,
            )
            return None

    if expected_audio_path is not None and stored_audio_hash is not None:
        audio_p = Path(expected_audio_path)
        if audio_p.is_file():
            actual_audio_hash = compute_file_sha256(audio_p).lower()
            if stored_audio_hash != actual_audio_hash:
                logger.warning(
                    "Sidecar %s possui audio_hash divergente do áudio real. "
                    "Descartando sidecar e acionando fallback proporcional.",
                    sidecar,
                )
                return None

    if expected_duration is not None and stored_duration is not None:
        try:
            dur_diff = abs(float(expected_duration) - float(stored_duration))
        except (TypeError, ValueError):
            logger.warning("Sidecar %s possui audio_duration_sec inválido. Acionando fallback.", sidecar)
            return None
        if dur_diff > 0.15:
            logger.warning(
                "Divergência temporal excessiva no sidecar %s (%.3fs vs %.3fs). "
                "Descartando sidecar e acionando fallback proporcional.",
                sidecar,
                float(stored_duration),
                float(expected_duration),
            )
            return None

    validated: list[dict] = []
    for item in timestamps:
        if not isinstance(item, dict):
            logger.warning("Item inválido no sidecar %s. Acionando fallback.", sidecar)
            return None
        if "word" not in item or "start" not in item or "end" not in item:
            logger.warning("Campos obrigatórios ausentes em item do sidecar %s. Acionando fallback.", sidecar)
            return None
        try:
            start_val = float(item["start"])
            end_val = float(item["end"])
        except (TypeError, ValueError):
            logger.warning("Timestamps não numéricos no sidecar %s. Acionando fallback.", sidecar)
            return None
        if start_val < 0.0 or end_val <= start_val:
            logger.warning("Intervalo temporal inválido no sidecar %s (%s..%s). Acionando fallback.", sidecar, start_val, end_val)
            return None
        validated.append(item)

    return validated


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
    last_word_timestamps: list[dict] | None = None

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
        self.last_word_timestamps: list[dict] | None = None

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
        self.last_word_timestamps = None
        output_path.with_suffix(".words.json").unlink(missing_ok=True)
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
        self.last_word_timestamps: list[dict] | None = None

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
        self.last_word_timestamps = None
        output_path.with_suffix(".words.json").unlink(missing_ok=True)
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

        sample_rate = 24000
        num_frames = int(duration * sample_rate)
        with wave.open(str(output_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(b"\x00\x00" * num_frames)
        return output_path, duration


class EdgeTTSVoiceSynthesizer(BaseVoiceSynthesizer):
    """Síntese de voz neural ultra-realista pt-BR via edge-tts com normalização loudnorm."""

    def __init__(self, voice: str | None = None, rate: str | None = None):
        settings = get_settings()
        self.voice = voice or settings.edge_tts_voice
        self.rate = rate or settings.edge_tts_rate
        self.last_word_timestamps: list[dict] | None = None

    def synthesize(
        self,
        text: str,
        output_path: Path,
        speaker_wav: Path | None = None,
    ) -> tuple[Path, float]:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temp_mp3 = output_path.with_suffix(".edge.temp.mp3")
        sidecar_path = output_path.with_suffix(".words.json")

        # Limpeza preemptiva para impedir reuso de estado ou sidecar obsoleto
        self.last_word_timestamps = None
        sidecar_path.unlink(missing_ok=True)
        word_timestamps: list[dict] = []

        try:
            import edge_tts

            async def _run():
                communicate = edge_tts.Communicate(
                    text,
                    self.voice,
                    rate=self.rate,
                    boundary="WordBoundary",
                )
                with open(temp_mp3, "wb") as mp3_file:
                    async for chunk in communicate.stream():
                        chunk_type = chunk.get("type")
                        if chunk_type == "audio":
                            mp3_file.write(chunk["data"])
                        elif chunk_type == "WordBoundary":
                            start_sec = float(chunk["offset"]) / 10_000_000.0
                            dur_sec = float(chunk["duration"]) / 10_000_000.0
                            end_sec = start_sec + dur_sec
                            word_timestamps.append({
                                "word": str(chunk["text"]),
                                "start": round(start_sec, 4),
                                "end": round(end_sec, 4),
                                "duration": round(dur_sec, 4),
                            })

            asyncio.run(_run())

            if not shutil.which("ffmpeg"):
                raise RuntimeError("FFmpeg é obrigatório para converter a síntese Edge-TTS MP3 para WAV.")

            if temp_mp3.exists() and temp_mp3.stat().st_size > 0:
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
            else:
                raise RuntimeError("Falha na síntese Edge-TTS: arquivo MP3 intermediário não foi gerado.")

            duration = probe_duration(output_path)
            if duration <= 0.0:
                raise RuntimeError(f"FFprobe retornou duração inválida ({duration}s) para {output_path}")

            if word_timestamps:
                self.last_word_timestamps = word_timestamps
                metadata = {
                    "schema_version": "1.0",
                    "audio_file": output_path.name,
                    "audio_duration_sec": round(duration, 3),
                    "audio_hash": compute_file_sha256(output_path),
                    "text_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                    "word_count": len(word_timestamps),
                    "timestamps": word_timestamps,
                }
                sidecar_path.write_text(
                    json.dumps(metadata, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
            else:
                logger.warning("Síntese Edge-TTS concluída sem eventos WordBoundary; fallback proporcional será usado.")

            return output_path, duration
        finally:
            if temp_mp3.exists():
                temp_mp3.unlink(missing_ok=True)


class PreSynthesizedVoice(BaseVoiceSynthesizer):
    """Sintetizador que entrega cópias com verificação de integridade de um áudio WAV pré-sintetizado.

    Garante que múltiplos cenários compartilhem rigorosamente o mesmo áudio físico,
    eliminando variações de síntese e verificando formato, hash e texto solicitado.
    """

    def __init__(
        self,
        master_audio_path: Path,
        duration: float,
        sha256_hash: str,
        expected_text: str,
    ):
        self.master_audio_path = Path(master_audio_path).resolve()
        self.duration = float(duration)
        self.sha256_hash = sha256_hash
        self.expected_text = expected_text.strip()
        self.delivered_copies: list[dict[str, Any]] = []
        self.last_word_timestamps: list[dict] | None = None
        self._validate_master_wav()

    def _validate_master_wav(self) -> None:
        if not self.master_audio_path.exists():
            raise FileNotFoundError(f"Áudio mestre não encontrado em {self.master_audio_path}")

        raw_bytes = self.master_audio_path.read_bytes()
        if not (raw_bytes.startswith(b"RIFF") and b"WAVE" in raw_bytes[:16]):
            raise ValueError(f"O áudio mestre {self.master_audio_path} não possui cabeçalho RIFF/WAVE legítimo.")

        calc_hash = hashlib.sha256(raw_bytes).hexdigest()
        if calc_hash != self.sha256_hash:
            raise ValueError(
                f"Hash SHA-256 do áudio mestre ({calc_hash}) diverge do hash esperado ({self.sha256_hash})."
            )

        if shutil.which("ffprobe"):
            proc = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=format_name:stream=codec_name",
                    "-of",
                    "json",
                    str(self.master_audio_path),
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            data = json.loads(proc.stdout or "{}")
            fmt = data.get("format", {}).get("format_name", "")
            streams = data.get("streams", [])
            codec = streams[0].get("codec_name", "") if streams else ""
            if "wav" not in fmt:
                raise ValueError(f"Formato FFprobe do áudio mestre não é WAV: {fmt}")
            if codec and "pcm" not in codec:
                raise ValueError(f"Codec do áudio mestre não é PCM: {codec}")

    def synthesize(
        self,
        text: str,
        output_path: Path,
        speaker_wav: Path | None = None,
    ) -> tuple[Path, float]:
        if text.strip() != self.expected_text:
            raise ValueError(
                f"Texto solicitado diverge do áudio pré-sintetizado mestre.\n"
                f"Esperado: {self.expected_text}\n"
                f"Recebido: {text.strip()}"
            )

        target = Path(output_path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target_sidecar = target.with_suffix(".words.json")
        target_sidecar.unlink(missing_ok=True)
        self.last_word_timestamps = None

        shutil.copy2(self.master_audio_path, target)

        delivered_hash = hashlib.sha256(target.read_bytes()).hexdigest()
        if delivered_hash != self.sha256_hash:
            raise ValueError(f"Corrupção de integridade na entrega do áudio copiado para {target}")

        master_sidecar = self.master_audio_path.with_suffix(".words.json")
        if master_sidecar.is_file():
            validated_ts = load_and_validate_word_timestamps(
                master_sidecar,
                expected_text=text,
                expected_duration=self.duration,
                expected_audio_path=self.master_audio_path,
            )
            if validated_ts is not None:
                shutil.copy2(master_sidecar, target_sidecar)
                self.last_word_timestamps = validated_ts

        self.delivered_copies.append({
            "path": str(target),
            "sha256": delivered_hash,
            "duration": self.duration,
        })
        return target, self.duration


class FallbackVoiceSynthesizer(BaseVoiceSynthesizer):
    """Cadeia de sintetizadores: XTTS v2 (se configurado e com voz de referência) -> Edge-TTS pt-BR -> Mock."""

    def __init__(self, synthesizers: list[BaseVoiceSynthesizer] | None = None):
        self.last_word_timestamps: list[dict] | None = None
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
        self.last_word_timestamps = None
        errors = []
        for syn in self.synthesizers:
            name = syn.__class__.__name__
            try:
                logger.info("Tentando síntese de voz com %s...", name)
                out, dur = syn.synthesize(text, output_path, speaker_wav=speaker_wav)
                self.last_word_timestamps = getattr(syn, "last_word_timestamps", None)
                logger.info("Voz sintetizada com sucesso via %s (duração: %.2fs)", name, dur)
                return out, dur
            except Exception as exc:
                logger.warning("Falha no sintetizador %s: %s. Tentando próximo...", name, exc)
                errors.append(f"{name}: {exc}")

        raise RuntimeError(f"Todos os sintetizadores de voz falharam: {'; '.join(errors)}")


