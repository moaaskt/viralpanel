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
from viralpanel.publishing.base import MockPublisher
from viralpanel.publishing.service import PublishingService
from viralpanel.scripting.gemini import FallbackScriptWriter, MockGeminiScriptWriter
from viralpanel.scripting.service import ScriptingService
from viralpanel.studio.avatar import MockAvatarAnimator
from viralpanel.studio.service import StudioService
from viralpanel.studio.voice import MockVoiceSynthesizer
from viralpanel.telegram.client import MockTelegramClient, TelegramClient
from viralpanel.telegram.service import SupervisionService


def build_default_services(
    mock: bool | None = None,
) -> tuple[DiscoveryService, ScriptingService, StudioService, SupervisionService, PublishingService]:
    settings = get_settings()
    mock = settings.pipeline_mock_mode if mock is None else mock
    studio = StudioService(
        voice_synthesizer=MockVoiceSynthesizer(),
        avatar_animator=MockAvatarAnimator(),
    )
    if mock or not settings.telegram_bot_token:
        tg_client = MockTelegramClient()
    else:
        tg_client = TelegramClient(
            bot_token=settings.telegram_bot_token,
            default_chat_id=settings.telegram_chat_id,
        )
    supervision = SupervisionService(
        client=tg_client,
        supervised_mode=settings.telegram_supervised_mode,
    )

    if mock:
        publishing = PublishingService(
            publishers={
                "tiktok": MockPublisher("tiktok"),
                "instagram": MockPublisher("instagram"),
                "youtube": MockPublisher("youtube"),
            },
            notifier=supervision.notifier,
        )
        return (
            DiscoveryService(scraper=MockDiscoveryScraper()),
            ScriptingService(MockMediaDownloader(), MockTranscriber(), MockGeminiScriptWriter()),
            studio,
            supervision,
            publishing,
        )

    publishing = PublishingService(notifier=supervision.notifier)
    return (
        DiscoveryService(scraper=TikTokDiscoveryScraper(use_fallback=False)),
        ScriptingService(
            MediaDownloader(),
            WhisperTranscriber(model_size=settings.whisper_model),
            FallbackScriptWriter(),
        ),
        studio,
        supervision,
        publishing,
    )


def _run_pipeline(
    run: PipelineRun,
    db: Session,
    discovery_service: DiscoveryService,
    scripting_service: ScriptingService | None,
    studio_service: StudioService | None,
    supervision_service: SupervisionService | None,
    publishing_service: PublishingService | None,
) -> dict:
    summary: dict = dict(run.run_metadata or {})

    if supervision_service:
        supervision_service.notifier.notify_pipeline_started(run.id, summary.get("run_date", ""))

    run.stage = "discovery"
    db.commit()
    candidates, best = discovery_service.run_discovery_cycle(db=db)
    summary.update(
        collected_count=len(candidates),
        selected_video_id=best.id if best else None,
        selected_video_url=best.url if best else None,
        selected_video_score=best.score if best else None,
    )
    if supervision_service:
        supervision_service.notifier.notify_stage_completed(
            run.id,
            "discovery",
            {"collected": len(candidates), "selected_score": best.score if best else None},
        )

    if best is None or scripting_service is None:
        return summary

    run.stage = "scripting"
    db.commit()
    script = scripting_service.process(db=db, run_id=run.id, source=best)
    summary.update(script_id=script.id, script_hook=script.hook)
    if supervision_service:
        supervision_service.notifier.notify_stage_completed(
            run.id, "scripting", {"script_id": script.id, "hook": script.hook}
        )

    if studio_service is None:
        return summary

    run.stage = "production"
    db.commit()
    final_asset = studio_service.produce(db=db, run_id=run.id, script=script)
    summary.update(
        final_asset_id=final_asset.id,
        final_video_path=final_asset.file_path,
        final_video_duration=final_asset.duration_seconds,
    )
    if supervision_service:
        supervision_service.notifier.notify_stage_completed(
            run.id,
            "production",
            {"final_asset_id": final_asset.id, "duration": final_asset.duration_seconds},
        )

    if supervision_service is None:
        return summary

    run.stage = "supervision"
    run.run_metadata = summary
    db.commit()
    approval_status = supervision_service.handle_post_production(
        db=db,
        run=run,
        final_asset=final_asset,
        hook=script.hook or "",
        score=best.score,
    )
    summary["approval_status"] = approval_status

    # Se aprovado (modo automático ou pré-aprovado), avança diretamente para a publicação oficial
    if approval_status == "approved" and publishing_service:
        run.stage = "publishing"
        db.commit()
        publications = publishing_service.publish_asset(
            db=db,
            asset=final_asset,
            script=script,
        )
        summary["published_count"] = len(publications)
        summary["published_urls"] = [p.url for p in publications if p.url]
        supervision_service.notifier.notify_stage_completed(
            run.id,
            "publishing",
            {"published_count": len(publications), "platforms": [p.platform for p in publications]},
        )

    supervision_service.notifier.notify_pipeline_success(run.id, summary)
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
    studio_service: StudioService | None = None,
    supervision_service: SupervisionService | None = None,
    publishing_service: PublishingService | None = None,
):
    run_date = run_date or date.today().isoformat()
    locker = locker or IdempotencyManager()
    key = f"daily:{run_date}"
    if not locker.acquire_lock(key, ttl_seconds=6 * 3600):
        return {"status": "skipped", "reason": "duplicate", "run_date": run_date}

    if discovery_service is None:
        (
            discovery_service,
            default_scripting,
            default_studio,
            default_supervision,
            default_publishing,
        ) = build_default_services()
        scripting_service = scripting_service or default_scripting
        studio_service = studio_service or default_studio
        supervision_service = supervision_service or default_supervision
        publishing_service = publishing_service or default_publishing

    factory = session_factory or SessionLocal
    start = time.monotonic()
    with factory() as db:
        run = PipelineRun(stage="init", status="running", run_metadata={"run_date": run_date})
        db.add(run)
        db.commit()
        try:
            run.run_metadata = _run_pipeline(
                run,
                db,
                discovery_service,
                scripting_service,
                studio_service,
                supervision_service,
                publishing_service,
            )
            run.status = "success"
        except Exception as exc:
            db.rollback()
            run.status = "failed"
            run.error_message = str(exc)
            if supervision_service:
                supervision_service.notifier.notify_error(run.id, run.stage, str(exc))
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
            "final_asset_id": meta.get("final_asset_id"),
            "approval_status": meta.get("approval_status"),
            "published_count": meta.get("published_count", 0),
        }
