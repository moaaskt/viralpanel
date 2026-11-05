from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from viralpanel.database import Base
from viralpanel.models import Asset, PipelineRun, Publication, Script, SourceVideo
from viralpanel.publishing.base import MockPublisher
from viralpanel.publishing.service import PublishingService
from viralpanel.telegram.client import MockTelegramClient
from viralpanel.telegram.notifier import TelegramNotifier


def _setup_db_with_asset(tmp_path):
    eng = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    factory = sessionmaker(bind=eng, expire_on_commit=False)

    video_file = tmp_path / "final_reaction_9x16.mp4"
    video_file.write_bytes(b"MOCKMP4DATA")

    with factory() as db:
        src = SourceVideo(url="https://www.tiktok.com/@creator/video/101", author="creator", score=110.0, status="approved")
        db.add(src)
        db.flush()
        script = Script(
            source_video_id=src.id,
            hook="Comece hoje, não espere a segunda-feira.",
            script_text="Comece hoje, não espere a segunda-feira. Pequenas vitórias consistentes geram grandes transformações.",
            version=1,
        )
        db.add(script)
        db.flush()
        asset = Asset(script_id=script.id, asset_type="final_video", file_path=str(video_file), duration_seconds=18.0)
        db.add(asset)
        db.commit()
        return factory, asset.id, script.id


def test_publishing_service_persists_publications(tmp_path):
    factory, asset_id, script_id = _setup_db_with_asset(tmp_path)
    tg_client = MockTelegramClient()
    notifier = TelegramNotifier(client=tg_client)

    service = PublishingService(
        publishers={
            "tiktok": MockPublisher("tiktok"),
            "instagram": MockPublisher("instagram"),
            "youtube": MockPublisher("youtube"),
        },
        notifier=notifier,
    )

    with factory() as db:
        asset = db.get(Asset, asset_id)
        script = db.get(Script, script_id)
        publications = service.publish_asset(db=db, asset=asset, script=script)

        assert len(publications) == 3
        platforms = {p.platform for p in publications}
        assert platforms == {"tiktok", "instagram", "youtube"}

        db_pubs = db.scalars(select(Publication).where(Publication.asset_id == asset.id)).all()
        assert len(db_pubs) == 3
        for pub in db_pubs:
            assert pub.status == "published"
            assert pub.url is not None
            assert pub.published_at is not None

        # Confirma notificação enviada no Telegram com links
        assert len(tg_client.messages) == 1
        msg = tg_client.messages[0]["text"]
        assert "Vídeo Publicado com Sucesso" in msg
        assert "Tiktok:" in msg
        assert "Instagram:" in msg
        assert "Youtube:" in msg

