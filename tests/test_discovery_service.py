from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from viralpanel.database import Base
from viralpanel.discovery.service import DiscoveryService
from viralpanel.discovery.tiktok import MockDiscoveryScraper
from viralpanel.models import SourceVideo


def _make_session():
    eng = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    return sessionmaker(bind=eng, expire_on_commit=False)


def test_discovery_collects_30_videos_and_selects_best_pending():
    factory = _make_session()
    now = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)
    service = DiscoveryService(scraper=MockDiscoveryScraper(base_now=now))

    with factory() as db:
        candidates, best = service.run_discovery_cycle(db=db, limit=30, now=now)
        assert len(candidates) == 30
        assert best is not None
        assert best.status == "pending"
        assert best.score == candidates[0].score

        # Se marcarmos o melhor como 'processed', a próxima seleção pega o segundo melhor
        best.status = "processed"
        db.commit()

        next_best = service.select_best_candidate(db=db)
        assert next_best is not None
        assert next_best.id != best.id
        assert next_best.score == candidates[1].score


def test_discovery_deduplicates_existing_urls():
    factory = _make_session()
    now = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)
    service = DiscoveryService(scraper=MockDiscoveryScraper(base_now=now))

    with factory() as db:
        service.collect_and_rank(db=db, limit=30, now=now)
        service.collect_and_rank(db=db, limit=30, now=now)
        total = db.scalars(select(SourceVideo)).all()
        assert len(total) == 30
