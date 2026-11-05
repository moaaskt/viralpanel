import time
from datetime import date

from viralpanel.celery_app import celery_app
from viralpanel.database import SessionLocal
from viralpanel.idempotency import IdempotencyManager
from viralpanel.models import PipelineRun


def _run_pipeline(run_date: str) -> None:
    """Tracer stub: later phases plug discovery -> publish stages here."""


@celery_app.task(
    name="viralpanel.tasks.trigger_daily_pipeline",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=5,
)
def trigger_daily_pipeline(self, run_date: str | None = None, session_factory=None, locker=None):
    run_date = run_date or date.today().isoformat()
    locker = locker or IdempotencyManager()
    key = f"daily:{run_date}"
    if not locker.acquire_lock(key, ttl_seconds=6 * 3600):
        return {"status": "skipped", "reason": "duplicate", "run_date": run_date}

    factory = session_factory or SessionLocal
    start = time.monotonic()
    with factory() as db:
        run = PipelineRun(stage="trigger", status="running", run_metadata={"run_date": run_date})
        db.add(run)
        db.commit()
        try:
            _run_pipeline(run_date)
            run.status = "success"
        except Exception as exc:
            run.status = "failed"
            run.error_message = str(exc)
            locker.release_lock(key)
            raise
        finally:
            run.duration_seconds = time.monotonic() - start
            db.commit()
        return {"status": run.status, "run_id": run.id, "run_date": run_date}
