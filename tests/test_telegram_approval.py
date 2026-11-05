from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from viralpanel.database import Base
from viralpanel.models import Asset, PipelineRun, Script, SourceVideo
from viralpanel.telegram.client import MockTelegramClient
from viralpanel.telegram.service import SupervisionService


def _setup_db_with_produced_video(tmp_path):
    eng = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    factory = sessionmaker(bind=eng, expire_on_commit=False)

    video_file = tmp_path / "final_reaction_9x16.mp4"
    video_file.write_bytes(b"MOCKMP4DATA")

    with factory() as db:
        src = SourceVideo(url="https://www.tiktok.com/@creator/video/777", author="creator", score=125.0, status="produced")
        db.add(src)
        db.flush()
        script = Script(source_video_id=src.id, hook="Disciplina vence talento.", script_text="Texto completo.", version=1)
        db.add(script)
        db.flush()
        asset = Asset(script_id=script.id, asset_type="final_video", file_path=str(video_file), duration_seconds=15.0)
        db.add(asset)
        db.flush()
        run = PipelineRun(
            stage="supervision",
            status="running",
            run_metadata={"final_asset_id": asset.id, "selected_video_id": src.id},
        )
        db.add(run)
        db.commit()
        return factory, run.id, asset.id, src.id


def test_supervised_mode_sends_video_preview_and_handles_approve_reject(tmp_path):
    factory, run_id, asset_id, src_id = _setup_db_with_produced_video(tmp_path)
    client = MockTelegramClient()
    service = SupervisionService(client=client, supervised_mode=True)

    with factory() as db:
        run = db.get(PipelineRun, run_id)
        asset = db.get(Asset, asset_id)
        status = service.handle_post_production(db, run, asset, hook="Disciplina vence talento.", score=125.0)
        assert status == "awaiting_approval"
        assert len(client.videos) == 1

        keyboard = client.videos[0]["reply_markup"]["inline_keyboard"][0]
        assert keyboard[0]["callback_data"] == f"approve:{run_id}"
        assert keyboard[1]["callback_data"] == f"reject:{run_id}"

        # Simula clique em Aprovar
        decision = service.process_callback(db, f"approve:{run_id}", callback_query_id="cb-1")
        assert decision == "approved"
        assert db.get(SourceVideo, src_id).status == "approved"
        assert db.get(PipelineRun, run_id).run_metadata["approval_status"] == "approved"
        assert client.callbacks_answered[0]["callback_query_id"] == "cb-1"

        # Simula clique em Rejeitar
        decision_reject = service.process_callback(db, f"reject:{run_id}", callback_query_id="cb-2")
        assert decision_reject == "rejected"
        assert db.get(SourceVideo, src_id).status == "rejected"


def test_unsupervised_mode_auto_approves_without_video_prompt(tmp_path):
    factory, run_id, asset_id, src_id = _setup_db_with_produced_video(tmp_path)
    client = MockTelegramClient()
    service = SupervisionService(client=client, supervised_mode=False)

    with factory() as db:
        run = db.get(PipelineRun, run_id)
        asset = db.get(Asset, asset_id)
        status = service.handle_post_production(db, run, asset, hook="Auto hook", score=99.0)
        assert status == "approved"
        assert len(client.videos) == 0
        assert db.get(SourceVideo, src_id).status == "approved"

