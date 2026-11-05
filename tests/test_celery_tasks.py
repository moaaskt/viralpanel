import pytest

fakeredis = pytest.importorskip("fakeredis")

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from viralpanel.celery_app import celery_app
from viralpanel.database import Base
from viralpanel.idempotency import IdempotencyManager
from viralpanel.models import PipelineRun
from viralpanel.storage import StorageManager
from viralpanel.tasks import build_default_services, trigger_daily_pipeline


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

    discovery, scripting = build_default_services(mock=True)
    scripting.downloader.storage = StorageManager(tmp_path)
    kw = {"session_factory": factory, "locker": locker, "discovery_service": discovery, "scripting_service": scripting}

    r1 = trigger_daily_pipeline.apply(args=["2026-01-01"], kwargs=kw).get()
    r2 = trigger_daily_pipeline.apply(args=["2026-01-01"], kwargs=kw).get()

    assert r1["status"] == "success"
    assert r1["selected_video_id"] and r1["script_id"]
    assert r2["status"] == "skipped"
    with factory() as s:
        assert len(s.scalars(select(PipelineRun)).all()) == 1
