from datetime import datetime, timedelta, timezone
import json

from viralpanel.discovery.base import ScrapedVideoMetadata
from viralpanel.discovery.scoring import ScoringConfig, calculate_viral_score, load_scoring_config
from viralpanel.discovery.utils import netscape_to_patchright_storage


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


def test_viral_score_duration_filter():
    now = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)
    cfg = ScoringConfig()

    too_short = ScrapedVideoMetadata(
        url="https://www.tiktok.com/@creator/video/short",
        author="creator",
        views=50_000,
        likes=5_000,
        comments=200,
        shares=300,
        duration=8,
        posted_at=now - timedelta(hours=3),
    )
    too_long = ScrapedVideoMetadata(
        url="https://www.tiktok.com/@creator/video/long",
        author="creator",
        views=50_000,
        likes=5_000,
        comments=200,
        shares=300,
        duration=240,
        posted_at=now - timedelta(hours=3),
    )
    ideal = ScrapedVideoMetadata(
        url="https://www.tiktok.com/@creator/video/ideal",
        author="creator",
        views=50_000,
        likes=5_000,
        comments=200,
        shares=300,
        duration=45,
        posted_at=now - timedelta(hours=3),
    )

    assert calculate_viral_score(too_short, config=cfg, now=now) == 0.0
    assert calculate_viral_score(too_long, config=cfg, now=now) == 0.0
    assert calculate_viral_score(ideal, config=cfg, now=now) > 0.0


def test_netscape_to_patchright_storage_parses_txt_and_json(tmp_path):
    netscape_file = tmp_path / "cookies.txt"
    netscape_file.write_text(
        "# Netscape HTTP Cookie File\n"
        ".tiktok.com\tTRUE\t/\tTRUE\t1893456000\tsessionid\tabc123xyz\n"
        "#HttpOnly_.tiktok.com\tTRUE\t/\tFALSE\t0\tsid_tt\tsecret_token\n",
        encoding="utf-8",
    )
    state = netscape_to_patchright_storage(netscape_file)
    assert len(state["cookies"]) == 2
    assert state["cookies"][0]["name"] == "sessionid"
    assert state["cookies"][0]["value"] == "abc123xyz"
    assert state["cookies"][0]["secure"] is True
    assert state["cookies"][0]["httpOnly"] is False
    assert state["cookies"][1]["name"] == "sid_tt"
    assert state["cookies"][1]["httpOnly"] is True
    assert state["cookies"][1]["expires"] == -1.0

    json_file = tmp_path / "cookies.json"
    json_file.write_text(
        json.dumps([{"name": "tt_webid", "value": "999", "domain": ".tiktok.com"}]),
        encoding="utf-8",
    )
    json_state = netscape_to_patchright_storage(json_file)
    assert len(json_state["cookies"]) == 1
    assert json_state["cookies"][0]["name"] == "tt_webid"


