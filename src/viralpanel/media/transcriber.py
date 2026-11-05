from abc import ABC, abstractmethod
from pathlib import Path

from pydantic import BaseModel


class TranscriptionSegment(BaseModel):
    start: float
    end: float
    text: str


class TranscriptionResult(BaseModel):
    text: str
    language: str | None = None
    segments: list[TranscriptionSegment]

    def to_timestamped_text(self) -> str:
        return "\n".join(f"[{s.start:06.2f}-{s.end:06.2f}] {s.text}" for s in self.segments)


class AudioTranscriber(ABC):
    @abstractmethod
    def transcribe(self, audio_path: Path) -> TranscriptionResult: ...


class WhisperTranscriber(AudioTranscriber):
    """faster-whisper (opcional: pip install faster-whisper)."""

    def __init__(self, model_size: str = "small", device: str = "auto", language: str | None = "pt"):
        self.model_size, self.device, self.language = model_size, device, language
        self._model = None

    def _load(self):
        if self._model is None:
            from faster_whisper import WhisperModel  # import tardio: dependência opcional
            self._model = WhisperModel(self.model_size, device=self.device, compute_type="int8")
        return self._model

    def transcribe(self, audio_path: Path) -> TranscriptionResult:
        segs, info = self._load().transcribe(str(audio_path), language=self.language, vad_filter=True)
        segments = [TranscriptionSegment(start=s.start, end=s.end, text=s.text.strip()) for s in segs]
        return TranscriptionResult(
            text=" ".join(s.text for s in segments), language=info.language, segments=segments,
        )


class MockTranscriber(AudioTranscriber):
    LINES = [
        "Você não precisa de motivação, precisa de disciplina.",
        "Todo dia que você adia, alguém mais disciplinado avança.",
        "Comece com cinco minutos e não quebre a corrente.",
        "Siga para mais conteúdos sobre mentalidade.",
    ]

    def transcribe(self, audio_path: Path) -> TranscriptionResult:
        segments, t = [], 0.0
        for line in self.LINES:
            segments.append(TranscriptionSegment(start=t, end=t + 3.0, text=line))
            t += 3.0
        return TranscriptionResult(text=" ".join(self.LINES), language="pt", segments=segments)

