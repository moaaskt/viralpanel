from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from viralpanel.database import Base
from viralpanel.models import Asset, Script, SourceVideo
from viralpanel.storage import StorageManager
from viralpanel.studio.avatar import MockAvatarAnimator
from viralpanel.studio.renderer import probe_video_dimensions
from viralpanel.studio.service import StudioService
from viralpanel.studio.subtitles import build_cues_from_script, write_ass_subtitles
from viralpanel.studio.voice import MockVoiceSynthesizer


def test_ass_subtitles_generation(tmp_path):
    cues = build_cues_from_script(
        "Pare de esperar motivação. Comece agora com cinco minutos de foco.",
        total_duration=4.0,
        max_words_per_cue=4,
    )
    assert len(cues) >= 2
    ass_file = write_ass_subtitles(cues, tmp_path / "subs.ass")
    content = ass_file.read_text(encoding="utf-8")
    assert "[V4+ Styles]" in content
    assert "Dialogue:" in content


def test_studio_service_renders_vertical_9x16_reaction_video(tmp_path):
    eng = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    factory = sessionmaker(bind=eng, expire_on_commit=False)

    service = StudioService(
        voice_synthesizer=MockVoiceSynthesizer(min_duration=1.5, max_duration=3.0),
        avatar_animator=MockAvatarAnimator(width=240, height=240),
        storage=StorageManager(tmp_path),
    )

    with factory() as db:
        src = SourceVideo(url="https://www.tiktok.com/@creator/video/99", author="creator", score=95.0)
        db.add(src)
        db.flush()
        script = Script(
            source_video_id=src.id,
            hook="Pare de adiar seus objetivos.",
            script_text="Pare de adiar seus objetivos. Cinco minutos hoje valem mais que promessas amanhã.",
            version=1,
        )
        db.add(script)
        db.commit()

        final_asset = service.produce(db=db, run_id="run-studio-1", script=script)
        assert final_asset.asset_type == "final_video"
        assert final_asset.duration_seconds and final_asset.duration_seconds >= 1.4

        width, height = probe_video_dimensions(tmp_path / "runs" / "run-studio-1" / "assets" / "final_reaction_9x16.mp4")
        assert (width, height) == (1080, 1920)
        assert src.status == "produced"

        all_assets = db.scalars(select(Asset).where(Asset.script_id == script.id)).all()
        asset_types = {a.asset_type for a in all_assets}
        assert {"audio", "avatar", "final_video"}.issubset(asset_types)
