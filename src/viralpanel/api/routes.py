"""REST API Routes for ViralPanel."""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from viralpanel.api.schemas import (
    AssetSchema,
    HealthResponse,
    PipelineRunSchema,
    PublicationSchema,
    ScriptSchema,
    SourceVideoSchema,
    StatsResponse,
    TriggerResponse,
)
from viralpanel.database import get_db_session
from viralpanel.models import Asset, PipelineRun, Publication, Script, SourceVideo

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def get_health(db: Session = Depends(get_db_session)) -> HealthResponse:
    """Return system health status."""
    db_status = "connected"
    try:
        db.execute(select(1)).scalar()
    except Exception as exc:
        db_status = f"error: {exc}"

    redis_status = "connected"
    try:
        from viralpanel.config import get_settings
        import redis
        settings = get_settings()
        r = redis.Redis.from_url(settings.redis_url, socket_timeout=1.0)
        r.ping()
    except Exception as exc:
        redis_status = f"error: {exc}"

    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        database=db_status,
        redis=redis_status,
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db_session)) -> StatsResponse:
    """Return aggregated platform metrics."""
    total_runs = db.scalar(select(func.count(PipelineRun.id))) or 0
    successful_runs = (
        db.scalar(
            select(func.count(PipelineRun.id)).where(PipelineRun.status == "completed")
        )
        or 0
    )
    failed_runs = (
        db.scalar(
            select(func.count(PipelineRun.id)).where(PipelineRun.status == "failed")
        )
        or 0
    )
    total_videos = db.scalar(select(func.count(SourceVideo.id))) or 0
    total_scripts = db.scalar(select(func.count(Script.id))) or 0
    total_publications = db.scalar(select(func.count(Publication.id))) or 0

    pub_by_platform_rows = db.execute(
        select(Publication.platform, func.count(Publication.id)).group_by(
            Publication.platform
        )
    ).all()
    pubs_dict = {str(platform): count for platform, count in pub_by_platform_rows}

    return StatsResponse(
        total_runs=total_runs,
        total_videos=total_videos,
        total_scripts=total_scripts,
        total_publications=total_publications,
        successful_runs=successful_runs,
        failed_runs=failed_runs,
        publications_by_platform=pubs_dict,
    )


@router.get("/runs", response_model=List[PipelineRunSchema])
def list_runs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db_session),
) -> List[PipelineRun]:
    """List execution pipeline runs ordered by start time desc."""
    stmt = (
        select(PipelineRun)
        .order_by(PipelineRun.started_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


@router.get("/runs/{run_id}", response_model=PipelineRunSchema)
def get_run(run_id: str, db: Session = Depends(get_db_session)) -> PipelineRun:
    """Get single pipeline run detail."""
    run = db.get(PipelineRun, run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline run {run_id} not found",
        )
    return run


@router.post("/runs/trigger", response_model=TriggerResponse)
def trigger_pipeline() -> TriggerResponse:
    """Trigger the daily automation pipeline manually via Celery."""
    try:
        from viralpanel.tasks import trigger_daily_pipeline
        task = trigger_daily_pipeline.delay()
        return TriggerResponse(
            task_id=str(task.id),
            message="Esteira diária disparada com sucesso na fila Celery.",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao disparar tarefa no Celery: {exc}",
        )


@router.get("/videos", response_model=List[SourceVideoSchema])
def list_videos(
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db_session),
) -> List[SourceVideo]:
    """List discovered source videos."""
    stmt = select(SourceVideo)
    if status_filter:
        stmt = stmt.where(SourceVideo.status == status_filter)
    stmt = stmt.order_by(SourceVideo.score.desc().nullslast(), SourceVideo.collected_at.desc())
    stmt = stmt.offset(offset).limit(limit)
    return list(db.scalars(stmt).all())


@router.get("/scripts", response_model=List[ScriptSchema])
def list_scripts(
    source_video_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db_session),
) -> List[Script]:
    """List generated scripts."""
    stmt = select(Script)
    if source_video_id:
        stmt = stmt.where(Script.source_video_id == source_video_id)
    stmt = stmt.order_by(Script.created_at.desc()).offset(offset).limit(limit)
    return list(db.scalars(stmt).all())


@router.get("/publications", response_model=List[PublicationSchema])
def list_publications(
    asset_id: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db_session),
) -> List[Publication]:
    """List publications and schedules."""
    stmt = select(Publication)
    if asset_id:
        stmt = stmt.where(Publication.asset_id == asset_id)
    if platform:
        stmt = stmt.where(Publication.platform == platform)
    stmt = stmt.order_by(Publication.published_at.desc().nullslast()).offset(offset).limit(limit)
    return list(db.scalars(stmt).all())


@router.get("/assets", response_model=List[AssetSchema])
def list_assets(
    script_id: Optional[str] = Query(None),
    asset_type: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db_session),
) -> List[Asset]:
    """List generated assets (audio, avatar, final video)."""
    stmt = select(Asset)
    if script_id:
        stmt = stmt.where(Asset.script_id == script_id)
    if asset_type:
        stmt = stmt.where(Asset.asset_type == asset_type)
    stmt = stmt.order_by(Asset.created_at.desc()).offset(offset).limit(limit)
    return list(db.scalars(stmt).all())
