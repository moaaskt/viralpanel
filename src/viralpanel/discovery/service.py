from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from viralpanel.discovery.base import BaseScraper, ScrapedVideoMetadata
from viralpanel.discovery.scoring import ScoringConfig, calculate_viral_score, load_scoring_config
from viralpanel.discovery.tiktok import TikTokDiscoveryScraper
from viralpanel.models import SourceVideo


class DiscoveryService:
    def __init__(
        self,
        scraper: BaseScraper | None = None,
        scoring_config: ScoringConfig | None = None,
    ):
        self.scoring_config = scoring_config or load_scoring_config()
        self.scraper = scraper or TikTokDiscoveryScraper()

    def collect_and_rank(
        self,
        db: Session,
        limit: int | None = None,
        now: datetime | None = None,
    ) -> list[SourceVideo]:
        target_limit = limit or self.scoring_config.discovery.default_limit
        hashtags = self.scoring_config.discovery.hashtags
        scraped_items: list[ScrapedVideoMetadata] = self.scraper.discover_trending(
            hashtags=hashtags,
            limit=target_limit,
        )

        ref_now = now or datetime.now(timezone.utc)
        persisted: list[SourceVideo] = []

        for item in scraped_items:
            score = calculate_viral_score(item, config=self.scoring_config, now=ref_now)
            existing = db.scalar(select(SourceVideo).where(SourceVideo.url == item.url))
            if existing is not None:
                existing.author = item.author
                existing.metrics = item.to_metrics_dict()
                existing.score = score
                existing.collected_at = ref_now
                persisted.append(existing)
            else:
                record = SourceVideo(
                    platform=item.platform,
                    url=item.url,
                    author=item.author,
                    metrics=item.to_metrics_dict(),
                    score=score,
                    collected_at=ref_now,
                    status="pending",
                )
                db.add(record)
                persisted.append(record)

        db.commit()
        for record in persisted:
            db.refresh(record)

        persisted.sort(key=lambda v: v.score or 0.0, reverse=True)
        return persisted

    def select_best_candidate(self, db: Session) -> SourceVideo | None:
        stmt = (
            select(SourceVideo)
            .where(SourceVideo.status == "pending")
            .order_by(SourceVideo.score.desc())
            .limit(1)
        )
        return db.scalar(stmt)

    def run_discovery_cycle(
        self,
        db: Session,
        limit: int | None = None,
        now: datetime | None = None,
    ) -> tuple[list[SourceVideo], SourceVideo | None]:
        candidates = self.collect_and_rank(db=db, limit=limit, now=now)
        best = self.select_best_candidate(db=db)
        return candidates, best

