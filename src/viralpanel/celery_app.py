from celery import Celery
from celery.schedules import crontab

from viralpanel.config import get_settings

settings = get_settings()

celery_app = Celery(
    "viralpanel",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["viralpanel.tasks"],
)

celery_app.conf.update(
    timezone=settings.timezone,
    enable_utc=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "daily-pipeline-trigger": {
            "task": "viralpanel.tasks.trigger_daily_pipeline",
            "schedule": crontab(hour=1, minute=0),
        }
    },
)
