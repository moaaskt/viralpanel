import re
from abc import ABC, abstractmethod
from pathlib import Path

from pydantic import BaseModel

# Padrões comuns de alucinação de modelos Whisper em silêncio ou apenas trilha sonora
HALLUCINATION_PATTERNS = [
    r"legendas\s+por",
    r"paulo\s+montenegro",
    r"amara\.org",
    r"subtitles\s+by",
    r"inscreva-se",
    r"deixe\s+seu\s+like",
    r"obrigado\s+por\s+assistir",
    r"curta\s+e\s+compartilhe",
    r"traduzido\s+por",
    r"transcrito\s+por",
]
HALLUCINATION_REGEX = re.compile("|".join(HALLUCINATION_PATTERNS), re.IGNORECASE)


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
    """faster-whisper com proteção contra alucinação de silêncio e música de fundo."""

    def __init__(self, model_size: str = "small", device: str = "auto", language: str | None = "pt"):
        self.model_size, self.device, self.language = model_size, device, language
        self._model = None

    def _load(self):
        if self._model is None:
            from faster_whisper import WhisperModel  # import tardio: dependência opcional
            self._model = WhisperModel(self.model_size, device=self.device, compute_type="int8")
        return self._model

    def _filter_hallucinations(self, segments: list[TranscriptionSegment]) -> list[TranscriptionSegment]:
        valid: list[TranscriptionSegment] = []
        for s in segments:
            clean = s.text.strip()
            # Se bater com padrão clássico de alucinação de silêncio, descarta
            if HALLUCINATION_REGEX.search(clean):
                continue
            if len(clean) >= 2:
                valid.append(s)
        return valid

    def transcribe(self, audio_path: Path) -> TranscriptionResult:
        # condition_on_previous_text=False previne repetição em loop e alucinações de legendas pré-treinadas
        segs, info = self._load().transcribe(
            str(audio_path),
            language=self.language,
            vad_filter=True,
            condition_on_previous_text=False,
        )
        raw_segments = [TranscriptionSegment(start=s.start, end=s.end, text=s.text.strip()) for s in segs]
        filtered_segments = self._filter_hallucinations(raw_segments)

        if not filtered_segments:
            # Retorna vazio limpo para acionar o fallback_context do vídeo original no ScriptingService
            return TranscriptionResult(text="", language=info.language or "pt", segments=[])

        return TranscriptionResult(
            text=" ".join(s.text for s in filtered_segments),
            language=info.language or "pt",
            segments=filtered_segments,
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
