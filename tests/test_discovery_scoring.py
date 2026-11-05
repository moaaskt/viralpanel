from datetime import datetime, timedelta, timezone

from viralpanel.discovery.base import ScrapedVideoMetadata
from viralpanel.discovery.scoring import ScoringConfig, calculate_viral_score, load_scoring_config


def test_load_scoring_config_from_yaml():
    cfg = load_scoring_config("config/scoring.yaml")
    assert cfg.weights.views == 0.25
    assert cfg.weights.engagement_ratio == 0.45
    assert cfg.weights.velocity_24h == 0.30
    assert cfg.discovery.default_limit == 30
    assert "desenvolvimentopessoal" in cfg.discovery.hashtags


def test_viral_score_below_min_views_returns_zero():
    now = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)
    video = ScrapedVideoMetadata(
        url="https://www.tiktok.com/@creator/video/1",
        author="creator",
        views=500,
        likes=100,
        comments=10,
        shares=5,
        posted_at=now - timedelta(hours=2),
    )
    assert calculate_viral_score(video, now=now) == 0.0


def test_recent_high_engagement_beats_old_low_engagement():
    now = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)
    cfg = ScoringConfig()

    recent_viral = ScrapedVideoMetadata(
        url="https://www.tiktok.com/@creator/video/recent",
        author="creator_a",
        views=150_000,
        likes=25_000,
        comments=2_000,
        shares=3_500,
        posted_at=now - timedelta(hours=6),
    )

    old_stagnant = ScrapedVideoMetadata(
        url="https://www.tiktok.com/@creator/video/old",
        author="creator_b",
        views=150_000,
        likes=3_000,
        comments=100,
        shares=50,
        posted_at=now - timedelta(days=14),
    )

    score_recent = calculate_viral_score(recent_viral, config=cfg, now=now)
    score_old = calculate_viral_score(old_stagnant, config=cfg, now=now)

    assert score_recent > score_old
    assert score_recent > 100.0
