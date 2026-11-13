from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from viralpanel.discovery.base import BaseScraper, ScrapedVideoMetadata
from viralpanel.discovery.scoring import ScoringConfig, calculate_viral_score, load_scoring_config
from viralpanel.discovery.tiktok import TikTokDiscoveryScraper, normalize_tiktok_url
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
        seed_accounts = self.scoring_config.discovery.seed_accounts
        search_queries = self.scoring_config.discovery.search_queries

        scraped_items: list[ScrapedVideoMetadata] = self.scraper.discover_trending(
            hashtags=hashtags,
            limit=target_limit,
            seed_accounts=seed_accounts,
            search_queries=search_queries,
        )

        ref_now = now or datetime.now(timezone.utc)
        persisted_map: dict[str, SourceVideo] = {}

        for item in scraped_items:
            norm_url = normalize_tiktok_url(item.url, default_author=item.author)
            score = calculate_viral_score(item, config=self.scoring_config, now=ref_now)
            existing = persisted_map.get(norm_url)
            if existing is None:
                existing = db.scalar(
                    select(SourceVideo).where((SourceVideo.url == item.url) | (SourceVideo.url == norm_url))
                )
            if existing is not None:
                existing.url = norm_url
                existing.author = item.author
                existing.metrics = item.to_metrics_dict()
                existing.score = score
                existing.collected_at = ref_now
                persisted_map[norm_url] = existing
            else:
                record = SourceVideo(
                    platform=item.platform,
                    url=norm_url,
                    author=item.author,
                    metrics=item.to_metrics_dict(),
                    score=score,
                    collected_at=ref_now,
                    status="pending",
                )
                db.add(record)
                persisted_map[norm_url] = record

        db.commit()
        persisted = list(persisted_map.values())
        for record in persisted:
            db.refresh(record)

        persisted.sort(key=lambda v: v.score or 0.0, reverse=True)
        return persisted

    def select_best_candidate(self, db: Session) -> SourceVideo | None:
        stmt = (
            select(SourceVideo)
            .where(SourceVideo.status == "pending", SourceVideo.score > 0.0)
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

