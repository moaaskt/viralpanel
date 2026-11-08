import pytest

fakeredis = pytest.importorskip("fakeredis")

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from viralpanel.celery_app import celery_app
from viralpanel.database import Base
from viralpanel.idempotency import IdempotencyManager
from viralpanel.models import Asset, PipelineRun, SourceVideo
from viralpanel.scripting.service import InsufficientSpeechError
from viralpanel.storage import StorageManager
from viralpanel.tasks import _run_pipeline, build_default_services, trigger_daily_pipeline


def test_beat_schedule_and_timezone():
    entry = celery_app.conf.beat_schedule["daily-pipeline-trigger"]
    assert celery_app.conf.timezone == "America/Sao_Paulo"
    assert entry["schedule"].hour == {1} and entry["schedule"].minute == {0}
    assert celery_app.conf.task_acks_late is True


def test_task_records_run_and_is_idempotent(tmp_path):
    eng = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    factory = sessionmaker(bind=eng, expire_on_commit=False)
    locker = IdempotencyManager(client=fakeredis.FakeRedis())

    discovery, scripting, studio, supervision, publishing = build_default_services(mock=True)
    storage = StorageManager(tmp_path)
    scripting.downloader.storage = storage
    studio.storage = storage
    kw = {
        "session_factory": factory,
        "locker": locker,
        "discovery_service": discovery,
        "scripting_service": scripting,
        "studio_service": studio,
        "supervision_service": supervision,
        "publishing_service": publishing,
    }

    r1 = trigger_daily_pipeline.apply(args=["2026-01-01"], kwargs=kw).get()
    r2 = trigger_daily_pipeline.apply(args=["2026-01-01"], kwargs=kw).get()

    assert r1["status"] == "success"
    assert r1["selected_video_id"] and r1["script_id"] and r1["final_asset_id"]
    assert r1["approval_status"] in ("awaiting_approval", "approved")
    assert r2["status"] == "skipped"
    with factory() as s:
        assert len(s.scalars(select(PipelineRun)).all()) == 1


def test_task_falls_back_to_next_candidate_on_insufficient_speech(tmp_path):
    eng = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    factory = sessionmaker(bind=eng, expire_on_commit=False)
    locker = IdempotencyManager(client=fakeredis.FakeRedis())

    discovery, scripting, studio, supervision, publishing = build_default_services(mock=True)
    storage = StorageManager(tmp_path)
    scripting.downloader.storage = storage
    studio.storage = storage

    original_process = scripting.process
    calls = {"count": 0}

    def flaky_process(db, run_id, source):
        calls["count"] += 1
        if calls["count"] == 1:
            source.status = "skipped_no_speech"
            db.commit()
            raise InsufficientSpeechError(f"Vídeo {source.url} sem fala")
        return original_process(db, run_id, source)

    scripting.process = flaky_process

    kw = {
        "session_factory": factory,
        "locker": locker,
        "discovery_service": discovery,
        "scripting_service": scripting,
        "studio_service": studio,
        "supervision_service": supervision,
        "publishing_service": publishing,
    }

    res = trigger_daily_pipeline.apply(args=["2026-01-02"], kwargs=kw).get()
    assert res["status"] == "success"
    assert calls["count"] == 2
    with factory() as s:
        skipped = s.scalars(select(SourceVideo).where(SourceVideo.status == "skipped_no_speech")).all()
        assert len(skipped) == 1


def test_run_pipeline_success(tmp_path):
    eng = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    factory = sessionmaker(bind=eng, expire_on_commit=False)

    discovery, scripting, studio, supervision, publishing = build_default_services(mock=True)
    storage = StorageManager(tmp_path)
    scripting.downloader.storage = storage
    studio.storage = storage

    with factory() as db:
        run = PipelineRun(status="running", stage="started", run_metadata={"run_date": "2026-01-03"})
        db.add(run)
        db.commit()

        summary = _run_pipeline(
            run=run,
            db=db,
            discovery_service=discovery,
            scripting_service=scripting,
            studio_service=studio,
            supervision_service=supervision,
            publishing_service=publishing,
        )

        assert summary["selected_video_id"] is not None
        assert summary["script_id"] is not None
        assert summary["final_asset_id"] is not None
        assert summary["final_video_path"] is not None
        assert summary["final_video_duration"] is not None

        # Verificar persistência dos assets no banco: 2 de scripting + 3 do studio
        assets = db.scalars(select(Asset).where(Asset.script_id == summary["script_id"])).all()
        assert len(assets) == 5
        types = {a.asset_type for a in assets}
        assert {"source_video", "source_audio", "audio", "avatar", "final_video"} == types

        # Verificar status do source video: transiciona por produced e chega em awaiting_approval/approved
        src_video = db.get(SourceVideo, summary["selected_video_id"])
        assert src_video is not None
        assert src_video.status in ("produced", "awaiting_approval", "approved")
        assert summary.get("approval_status") in ("awaiting_approval", "approved")

