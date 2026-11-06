import logging
from sqlalchemy.orm import Session

from viralpanel.media.downloader import MediaDownloader
from viralpanel.media.transcriber import AudioTranscriber, MockTranscriber
from viralpanel.models import Asset, Script, SourceVideo
from viralpanel.scripting.gemini import ScriptWriter

logger = logging.getLogger(__name__)

MIN_SPEECH_WORDS = 15


class InsufficientSpeechError(RuntimeError):
    """Levantada quando o vídeo transcrito possui menos palavras faladas que o mínimo exigido."""


class ScriptingService:
    """Download -> extração de áudio -> transcrição -> portão pós-Whisper -> roteiro IA -> persistência."""

    def __init__(
        self,
        downloader: MediaDownloader,
        transcriber: AudioTranscriber,
        writer: ScriptWriter,
        min_speech_words: int = MIN_SPEECH_WORDS,
    ):
        self.downloader = downloader
        self.transcriber = transcriber
        self.writer = writer
        self.min_speech_words = min_speech_words

    def process(self, db: Session, run_id: str, source: SourceVideo) -> Script:
        source.status = "analyzing"
        db.commit()
        try:
            video, audio = self.downloader.fetch(run_id, source.url)
            transcription = self.transcriber.transcribe(audio)

            # Portão Pós-Whisper: exige ao menos N palavras reais faladas (exceto se for MockTranscriber)
            words = [w for w in transcription.text.strip().split() if w.strip()]
            word_count = len(words)
            if not isinstance(self.transcriber, MockTranscriber) and word_count < self.min_speech_words:
                source.status = "skipped_no_speech"
                db.commit()
                msg = (
                    f"Vídeo {source.url} rejeitado: apenas {word_count} palavras faladas "
                    f"(mínimo exigido: {self.min_speech_words})"
                )
                logger.warning(msg)
                raise InsufficientSpeechError(msg)

            # Contexto complementar a partir dos metadados do vídeo fonte (título, autor, tags)
            fallback_context = ""
            if source.metrics and isinstance(source.metrics, dict):
                title = source.metrics.get("title", "")
                author = source.author or ""
                tags = " ".join(f"#{t}" for t in source.metrics.get("hashtags", []))
                fallback_context = f"Título/Descrição: {title} | Criador: @{author} | Tags: {tags}".strip()

            generated = self.writer.generate(transcription, fallback_context=fallback_context)

            last_version = max((s.version for s in source.scripts), default=0)
            metadata_json = {
                "factual_claims": [c.model_dump() for c in generated.factual_claims],
                "closing_thought": generated.closing_thought,
                "cta": generated.cta,
            }
            script = Script(
                source_video_id=source.id,
                transcription=transcription.model_dump_json(),
                script_text=generated.full_text,
                hook=generated.hook,
                version=last_version + 1,
                metadata_json=metadata_json,
            )
            db.add(script)
            db.flush()

            # Registra tanto o vídeo quanto o áudio como assets essenciais para a etapa de Studio (reaction 9:16)
            db.add(Asset(script_id=script.id, asset_type="source_video", file_path=str(video)))
            db.add(Asset(script_id=script.id, asset_type="source_audio", file_path=str(audio)))

            source.status = "scripted"
            db.commit()
            db.refresh(script)
            return script
        except InsufficientSpeechError:
            raise
        except Exception:
            db.rollback()
            source.status = "failed"
            db.commit()
            raise
