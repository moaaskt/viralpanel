import shutil
import subprocess
from pathlib import Path

from sqlalchemy.orm import Session

from viralpanel.branding import SafeZones9x16
from viralpanel.models import Asset, Script
from viralpanel.storage import StorageManager
from viralpanel.studio.avatar import AvatarConfig, BaseAvatarAnimator
from viralpanel.studio.renderer import (
    ReactionCompositionSpec,
    ReactionVideoRenderer,
    StudioRenderRequest,
    has_video_stream,
)
from viralpanel.studio.subtitles import SubtitleJobConfig, generate_subtitles
from viralpanel.studio.voice import BaseVoiceSynthesizer


class StudioService:
    """Orquestra Voz -> Avatar -> Legendas -> Renderização 9:16 e salva os Assets no banco."""

    def __init__(
        self,
        voice_synthesizer: BaseVoiceSynthesizer,
        avatar_animator: BaseAvatarAnimator,
        renderer: ReactionVideoRenderer | None = None,
        storage: StorageManager | None = None,
        avatar_config: AvatarConfig | None = None,
        composition: ReactionCompositionSpec | None = None,
    ):
        self.voice_synthesizer = voice_synthesizer
        self.avatar_animator = avatar_animator
        self.renderer = renderer or ReactionVideoRenderer()
        self.storage = storage or StorageManager()
        self.avatar_config = avatar_config or getattr(avatar_animator, "config", None)
        self.composition = composition or ReactionCompositionSpec()

    def _ensure_source_video(self, run_id: str, duration: float = 2.0) -> Path:
        source_dir = self.storage._safe(self.storage.get_run_dir(run_id).parent / "source")
        source_dir.mkdir(parents=True, exist_ok=True)
        video_path = source_dir / "source.mp4"
        if video_path.exists() and has_video_stream(video_path):
            return video_path

        if shutil.which("ffmpeg"):
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    f"color=c=#334155:s=360x640:r=24:d={duration}",
                    "-f",
                    "lavfi",
                    "-i",
                    f"sine=frequency=220:duration={duration}",
                    "-shortest",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    str(video_path),
                ],
                check=True,
                capture_output=True,
                timeout=60,
            )
        else:
            video_path.write_bytes(b"MOCKSOURCEVIDEO")
        return video_path

    def produce(self, db: Session, run_id: str, script: Script) -> Asset:
        assets_dir = self.storage.get_run_dir(run_id)
        script_text = script.script_text or script.hook or "Conteúdo de desenvolvimento pessoal."

        # 1. Síntese de Voz (XTTS / Mock)
        voice_path = assets_dir / "narration.wav"
        voice_path, voice_duration = self.voice_synthesizer.synthesize(script_text, voice_path)
        db.add(
            Asset(
                script_id=script.id,
                asset_type="audio",
                file_path=str(voice_path),
                duration_seconds=voice_duration,
            )
        )

        # 2. Animação do Avatar sincronizado
        avatar_path = assets_dir / "avatar.mp4"
        avatar_path, avatar_duration = self.avatar_animator.generate_avatar_video(voice_path, avatar_path)
        db.add(
            Asset(
                script_id=script.id,
                asset_type="avatar",
                file_path=str(avatar_path),
                duration_seconds=avatar_duration,
            )
        )

        # 3. Legendas ASS sincronizadas
        subtitles_path = assets_dir / "captions.ass"
        job_config = SubtitleJobConfig(
            script_text=script_text,
            total_duration=voice_duration,
            output_path=subtitles_path,
            margin_v=SafeZones9x16.SUBTITLE_MARGIN_V,
        )
        generate_subtitles(job_config)

        # 4. Composição 9:16 Reaction via FFmpeg
        source_video_path = self._ensure_source_video(run_id, duration=max(voice_duration, 2.0))
        final_video_path = assets_dir / "final_reaction_9x16.mp4"
        render_request = StudioRenderRequest(
            run_id=run_id,
            source_video_path=source_video_path,
            avatar_video_path=avatar_path,
            voice_audio_path=voice_path,
            ass_subtitle_path=subtitles_path,
            output_path=final_video_path,
            voice_duration=voice_duration,
            avatar_config=self.avatar_config,
            composition=self.composition,
        )

        if hasattr(self.renderer, "render_from_request"):
            final_video_path, final_duration = self.renderer.render_from_request(render_request)
        else:
            final_video_path, final_duration = self.renderer.render(
                source_video_path=source_video_path,
                avatar_video_path=avatar_path,
                voice_audio_path=voice_path,
                ass_subtitle_path=subtitles_path,
                output_path=final_video_path,
            )

        final_asset = Asset(
            script_id=script.id,
            asset_type="final_video",
            file_path=str(final_video_path),
            duration_seconds=final_duration,
        )
        db.add(final_asset)
        if script.source_video is not None:
            script.source_video.status = "produced"
        db.commit()
        db.refresh(final_asset)
        return final_asset

