from datetime import datetime, timezone
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from viralpanel.discovery.base import ScrapedVideoMetadata


class WeightsConfig(BaseModel):
    views: float = 0.25
    engagement_ratio: float = 0.45
    velocity_24h: float = 0.30


class EngagementMultipliers(BaseModel):
    likes: float = 1.0
    comments: float = 2.0
    shares: float = 3.0


class ThresholdsConfig(BaseModel):
    min_views: int = 1000
    reference_views: int = 100000
    reference_velocity_per_hour: float = 5000.0


class DiscoverySettings(BaseModel):
    default_limit: int = 30
    hashtags: list[str] = Field(
        default_factory=lambda: [
            "desenvolvimentopessoal",
            "motivacao",
            "mentalidade",
            "disciplina",
            "produtividade",
        ]
    )


class ScoringConfig(BaseModel):
    weights: WeightsConfig = Field(default_factory=WeightsConfig)
    engagement_multipliers: EngagementMultipliers = Field(default_factory=EngagementMultipliers)
    thresholds: ThresholdsConfig = Field(default_factory=ThresholdsConfig)
    discovery: DiscoverySettings = Field(default_factory=DiscoverySettings)


def load_scoring_config(path: str | Path = "config/scoring.yaml") -> ScoringConfig:
    cfg_path = Path(path)
    if not cfg_path.exists():
        return ScoringConfig()
    with cfg_path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    return ScoringConfig.model_validate(raw)


def calculate_viral_score(
    video: ScrapedVideoMetadata,
    config: ScoringConfig | None = None,
    now: datetime | None = None,
) -> float:
    cfg = config or ScoringConfig()
    if video.views < cfg.thresholds.min_views or video.views <= 0:
        return 0.0

    ref_now = now or datetime.now(timezone.utc)
    posted_at = video.posted_at
    if posted_at.tzinfo is None:
        posted_at = posted_at.replace(tzinfo=timezone.utc)

    hours_elapsed = max((ref_now - posted_at).total_seconds() / 3600.0, 1.0)

    # 1. Views normalizadas
    views_norm = min(video.views / max(cfg.thresholds.reference_views, 1), 3.0)

    # 2. Ratio de engajamento ponderado
    m = cfg.engagement_multipliers
    weighted_interactions = (
        video.likes * m.likes
        + video.comments * m.comments
        + video.shares * m.shares
    )
    engagement_ratio = weighted_interactions / video.views
    # Normaliza o ratio assumindo ~0.20 (20% de engajamento ponderado) como referência forte
    engagement_norm = min(engagement_ratio / 0.20, 3.0)

    # 3. Velocidade de crescimento (views/hora), com bônus para vídeos das últimas 24h
    velocity_per_hour = video.views / hours_elapsed
    recency_boost = 1.5 if hours_elapsed <= 24.0 else max(24.0 / hours_elapsed, 0.2)
    velocity_norm = min(
        (velocity_per_hour / max(cfg.thresholds.reference_velocity_per_hour, 1.0)) * recency_boost,
        3.0,
    )

    w = cfg.weights
    score = (
        views_norm * w.views
        + engagement_norm * w.engagement_ratio
        + velocity_norm * w.velocity_24h
    ) * 100.0
    return round(score, 4)
