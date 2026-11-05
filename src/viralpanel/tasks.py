import time
from datetime import date

from sqlalchemy.orm import Session

from viralpanel.celery_app import celery_app
from viralpanel.database import SessionLocal
from viralpanel.discovery.service import DiscoveryService
from viralpanel.discovery.tiktok import MockDiscoveryScraper
from viralpanel.idempotency import IdempotencyManager
from viralpanel.models import PipelineRun


def _run_pipeline(run_date: str, db: Session | None = None, discovery_service: DiscoveryService | None = None) -> dict:
    """Executa a etapa de Discovery & Scoring e retorna metadados do ciclo."""
    if db is None:
        return {"run_date": run_date}

    svc = discovery_service or DiscoveryService(scraper=MockDiscoveryScraper())
    candidates, best = svc.run_discovery_cycle(db=db)
    return {
        "run_date": run_date,
        "collected_count": len(candidates),
        "selected_video_id": best.id if best else None,
        "selected_video_url": best.url if best else None,
        "selected_video_score": best.score if best else None,
    }


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
):
    run_date = run_date or date.today().isoformat()
    locker = locker or IdempotencyManager()
    key = f"daily:{run_date}"
    if not locker.acquire_lock(key, ttl_seconds=6 * 3600):
        return {"status": "skipped", "reason": "duplicate", "run_date": run_date}

    factory = session_factory or SessionLocal
    start = time.monotonic()
    with factory() as db:
        run = PipelineRun(stage="discovery", status="running", run_metadata={"run_date": run_date})
        db.add(run)
        db.commit()
        try:
            summary = _run_pipeline(run_date, db=db, discovery_service=discovery_service)
            run.run_metadata = summary
            run.status = "success"
        except Exception as exc:
            run.status = "failed"
            run.error_message = str(exc)
            locker.release_lock(key)
            raise
        finally:
            run.duration_seconds = time.monotonic() - start
            db.commit()
        return {
            "status": run.status,
            "run_id": run.id,
            "run_date": run_date,
            "selected_video_id": run.run_metadata.get("selected_video_id") if run.run_metadata else None,
        }
