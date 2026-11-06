from sqlalchemy.orm import Session

from viralpanel.media.downloader import MediaDownloader
from viralpanel.media.transcriber import AudioTranscriber
from viralpanel.models import Asset, Script, SourceVideo
from viralpanel.scripting.gemini import ScriptWriter


class ScriptingService:
    """Download -> extração de áudio -> transcrição -> roteiro Gemini -> persistência."""

    def __init__(self, downloader: MediaDownloader, transcriber: AudioTranscriber, writer: ScriptWriter):
        self.downloader, self.transcriber, self.writer = downloader, transcriber, writer

    def process(self, db: Session, run_id: str, source: SourceVideo) -> Script:
        source.status = "analyzing"
        db.commit()
        try:
            video, audio = self.downloader.fetch(run_id, source.url)
            transcription = self.transcriber.transcribe(audio)

            # Contexto complementar a partir dos metadados do vídeo fonte (título, autor, tags)
            fallback_context = ""
            if source.metrics and isinstance(source.metrics, dict):
                title = source.metrics.get("title", "")
                author = source.author or ""
                tags = " ".join(f"#{t}" for t in source.metrics.get("hashtags", []))
                fallback_context = f"Título/Descrição: {title} | Criador: @{author} | Tags: {tags}".strip()

            generated = self.writer.generate(transcription, fallback_context=fallback_context)

            last_version = max((s.version for s in source.scripts), default=0)
            script = Script(
                source_video_id=source.id,
                transcription=transcription.model_dump_json(),
                script_text=generated.full_text,
                hook=generated.hook,
                version=last_version + 1,
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
        except Exception:
            db.rollback()
            source.status = "failed"
            db.commit()
            raise
