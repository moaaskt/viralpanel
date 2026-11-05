"""Unit and integration tests for ViralPanel REST API."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from viralpanel.api.app import create_app
from viralpanel.database import get_db_session
from viralpanel.models import Asset, Base, PipelineRun, Publication, Script, SourceVideo


@pytest.fixture(name="db_session")
def fixture_db_session():
    """In-memory SQLite DB session for API tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(name="client")
def fixture_client(db_session):
    """TestClient configured with overridden database dependency."""
    app = create_app()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db
    with TestClient(app) as test_client:
        yield test_client


def test_api_health(client):
    """Test health check endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["database"] == "connected"


def test_api_stats_empty(client):
    """Test stats endpoint on empty database."""
    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_runs"] == 0
    assert data["total_videos"] == 0
    assert data["total_scripts"] == 0
    assert data["total_publications"] == 0


def test_api_runs_crud_and_stats(client, db_session):
    """Test listing runs and statistics calculation."""
    run1 = PipelineRun(
        id="run-001",
        stage="publishing",
        status="completed",
        duration_seconds=12.5,
    )
    run2 = PipelineRun(
        id="run-002",
        stage="studio",
        status="failed",
        error_message="Test failure",
        duration_seconds=5.0,
    )
    db_session.add_all([run1, run2])
    db_session.commit()

    # Test /api/runs
    response = client.get("/api/runs")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    # Test /api/runs/{id}
    res_single = client.get(f"/api/runs/{run1.id}")
    assert res_single.status_code == 200
    assert res_single.json()["status"] == "completed"

    res_not_found = client.get("/api/runs/non-existent-id")
    assert res_not_found.status_code == 404

    # Test /api/stats with populated runs
    res_stats = client.get("/api/stats")
    assert res_stats.status_code == 200
    stats = res_stats.json()
    assert stats["total_runs"] == 2
    assert stats["successful_runs"] == 1
    assert stats["failed_runs"] == 1


def test_api_videos_scripts_and_assets(client, db_session):
    """Test listing source videos, scripts, and assets."""
    video = SourceVideo(
        id="sv-1",
        platform="tiktok",
        url="https://tiktok.com/@test/video/123",
        author="@coach_mindset",
        metrics={"views": 150000, "likes": 18000},
        score=88.5,
        status="selected",
    )
    db_session.add(video)
    db_session.flush()

    script = Script(
        id="sc-1",
        source_video_id=video.id,
        hook="Pare de procrastinar agora!",
        script_text="Texto completo do roteiro...",
        version=1,
    )
    db_session.add(script)
    db_session.flush()

    asset = Asset(
        id="as-1",
        script_id=script.id,
        asset_type="final_video",
        file_path="/tmp/test_final.mp4",
        duration_seconds=42.0,
    )
    pub = Publication(
        id="pb-1",
        asset_id=asset.id,
        platform="tiktok",
        status="published",
        url="https://tiktok.com/@me/video/999",
        published_at=datetime.now(timezone.utc),
    )
    db_session.add_all([asset, pub])
    db_session.commit()

    # Test /api/videos
    res_videos = client.get("/api/videos")
    assert res_videos.status_code == 200
    v_data = res_videos.json()
    assert len(v_data) == 1
    assert v_data[0]["id"] == "sv-1"
    assert v_data[0]["score"] == 88.5

    # Test /api/scripts
    res_scripts = client.get(f"/api/scripts?source_video_id={video.id}")
    assert res_scripts.status_code == 200
    s_data = res_scripts.json()
    assert len(s_data) == 1
    assert "Pare de procrastinar" in s_data[0]["hook"]

    # Test /api/assets
    res_assets = client.get(f"/api/assets?script_id={script.id}")
    assert res_assets.status_code == 200
    a_data = res_assets.json()
    assert len(a_data) == 1
    assert a_data[0]["asset_type"] == "final_video"

    # Test /api/publications
    res_pubs = client.get(f"/api/publications?platform=tiktok")
    assert res_pubs.status_code == 200
    p_data = res_pubs.json()
    assert len(p_data) == 1
    assert p_data[0]["platform"] == "tiktok"
    assert p_data[0]["url"] == "https://tiktok.com/@me/video/999"


@patch("viralpanel.tasks.trigger_daily_pipeline.delay")
def test_api_trigger_pipeline(mock_celery_delay, client):
    """Test triggering daily automation via API."""
    mock_task = MagicMock()
    mock_task.id = "mock-celery-task-12345"
    mock_celery_delay.return_value = mock_task

    response = client.post("/api/runs/trigger")
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == "mock-celery-task-12345"
    assert "sucesso" in data["message"]
    mock_celery_delay.assert_called_once()
