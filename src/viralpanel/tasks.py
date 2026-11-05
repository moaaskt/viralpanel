import time
from datetime import date

from sqlalchemy.orm import Session

from viralpanel.celery_app import celery_app
from viralpanel.config import get_settings
from viralpanel.database import SessionLocal
from viralpanel.discovery.service import DiscoveryService
from viralpanel.discovery.tiktok import MockDiscoveryScraper, TikTokDiscoveryScraper
from viralpanel.idempotency import IdempotencyManager
from viralpanel.media.downloader import MediaDownloader, MockMediaDownloader
from viralpanel.media.transcriber import MockTranscriber, WhisperTranscriber
from viralpanel.models import PipelineRun
from viralpanel.scripting.gemini import GeminiScriptWriter, MockGeminiScriptWriter
from viralpanel.scripting.service import ScriptingService


def build_default_services(mock: bool | None = None) -> tuple[DiscoveryService, ScriptingService]:
    settings = get_settings()
    mock = settings.pipeline_mock_mode if mock is None else mock
    if mock:
        return (
            DiscoveryService(scraper=MockDiscoveryScraper()),
            ScriptingService(MockMediaDownloader(), MockTranscriber(), MockGeminiScriptWriter()),
        )
    return (
        DiscoveryService(scraper=TikTokDiscoveryScraper()),
        ScriptingService(
            MediaDownloader(),
            WhisperTranscriber(model_size=settings.whisper_model),
            GeminiScriptWriter(),
        ),
    )


def _run_pipeline(
    run: PipelineRun,
    db: Session,
    discovery_service: DiscoveryService,
    scripting_service: ScriptingService | None,
) -> dict:
    summary: dict = dict(run.run_metadata or {})

    run.stage = "discovery"
    db.commit()
    candidates, best = discovery_service.run_discovery_cycle(db=db)
    summary.update(
        collected_count=len(candidates),
        selected_video_id=best.id if best else None,
        selected_video_url=best.url if best else None,
        selected_video_score=best.score if best else None,
    )
    if best is None or scripting_service is None:
        return summary

    run.stage = "scripting"
    db.commit()
    script = scripting_service.process(db=db, run_id=run.id, source=best)
    summary.update(script_id=script.id, script_hook=script.hook)
    return summary


@celery_app.task(
    name="viralpanel.tasks.trigger_daily_pipeline",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=5,
)
def trigger_daily_pipeline(
    self,
    run_date: str | None = None,
    session_factory=None,
    locker=None,
    discovery_service: DiscoveryService | None = None,
    scripting_service: ScriptingService | None = None,
):
    run_date = run_date or date.today().isoformat()
    locker = locker or IdempotencyManager()
    key = f"daily:{run_date}"
    if not locker.acquire_lock(key, ttl_seconds=6 * 3600):
        return {"status": "skipped", "reason": "duplicate", "run_date": run_date}

    if discovery_service is None:
        discovery_service, default_scripting = build_default_services()
        scripting_service = scripting_service or default_scripting

    factory = session_factory or SessionLocal
    start = time.monotonic()
    with factory() as db:
        run = PipelineRun(stage="init", status="running", run_metadata={"run_date": run_date})
        db.add(run)
        db.commit()
        try:
            run.run_metadata = _run_pipeline(run, db, discovery_service, scripting_service)
            run.status = "success"
        except Exception as exc:
            db.rollback()
            run.status = "failed"
            run.error_message = str(exc)
            locker.release_lock(key)
            raise
        finally:
            run.duration_seconds = time.monotonic() - start
            db.commit()
        meta = run.run_metadata or {}
        return {
            "status": run.status,
            "run_id": run.id,
            "run_date": run_date,
            "selected_video_id": meta.get("selected_video_id"),
            "script_id": meta.get("script_id"),
        }
