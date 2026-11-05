import json
import subprocess
from datetime import datetime, timedelta, timezone

from viralpanel.discovery.base import BaseScraper, ScrapedVideoMetadata


class MockDiscoveryScraper(BaseScraper):
    """Gerador determinístico de 30 vídeos de desenvolvimento pessoal para fallback e testes."""

    def __init__(self, base_now: datetime | None = None):
        self.base_now = base_now or datetime.now(timezone.utc)

    def discover_trending(
        self,
        hashtags: list[str] | None = None,
        limit: int = 30,
    ) -> list[ScrapedVideoMetadata]:
        tags = hashtags or ["desenvolvimentopessoal", "motivacao", "disciplina"]
        items: list[ScrapedVideoMetadata] = []
        for idx in range(1, limit + 1):
            hours_ago = (idx * 2) % 48 + 1
            views = 15_000 + (idx * 8_500)
            likes = int(views * (0.08 + (idx % 5) * 0.03))
            comments = int(likes * 0.06)
            shares = int(likes * 0.12)
            items.append(
                ScrapedVideoMetadata(
                    url=f"https://www.tiktok.com/@mentor_{idx}/video/{100000 + idx}",
                    platform="tiktok",
                    author=f"mentor_{idx}",
                    title=f"Segredo #{idx} de disciplina e foco #{tags[idx % len(tags)]}",
                    views=views,
                    likes=likes,
                    comments=comments,
                    shares=shares,
                    posted_at=self.base_now - timedelta(hours=hours_ago),
                    hashtags=[tags[idx % len(tags)]],
                )
            )
        return items


class TikTokDiscoveryScraper(BaseScraper):
    """Scraper TikTok utilizando yt-dlp / Playwright com fallback seguro para MockDiscoveryScraper."""

    def __init__(self, use_fallback: bool = True, timeout_seconds: int = 30):
        self.use_fallback = use_fallback
        self.timeout_seconds = timeout_seconds

    def _extract_via_ytdlp(self, hashtag: str, max_items: int) -> list[ScrapedVideoMetadata]:
        url = f"https://www.tiktok.com/tag/{hashtag}"
        cmd = [
            "yt-dlp",
            "--flat-playlist",
            "--dump-json",
            "--playlist-end",
            str(max_items),
            url,
        ]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
            check=True,
        )
        results: list[ScrapedVideoMetadata] = []
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            video_url = data.get("webpage_url") or data.get("url")
            if not video_url:
                continue
            ts = data.get("timestamp")
            posted_at = (
                datetime.fromtimestamp(ts, tz=timezone.utc)
                if ts
                else datetime.now(timezone.utc)
            )
            results.append(
                ScrapedVideoMetadata(
                    url=video_url,
                    platform="tiktok",
                    author=data.get("uploader") or data.get("creator") or "unknown",
                    title=data.get("title") or "",
                    views=int(data.get("view_count") or 0),
                    likes=int(data.get("like_count") or 0),
                    comments=int(data.get("comment_count") or 0),
                    shares=int(data.get("repost_count") or 0),
                    posted_at=posted_at,
                    hashtags=[hashtag],
                )
            )
        return results

    def discover_trending(
        self,
        hashtags: list[str] | None = None,
        limit: int = 30,
    ) -> list[ScrapedVideoMetadata]:
        tags = hashtags or ["desenvolvimentopessoal", "motivacao", "disciplina"]
        collected: dict[str, ScrapedVideoMetadata] = {}
        per_tag = max(limit // max(len(tags), 1), 10)

        try:
            for tag in tags:
                for item in self._extract_via_ytdlp(tag, max_items=per_tag):
                    collected[item.url] = item
                    if len(collected) >= limit:
                        return list(collected.values())[:limit]
        except Exception:
            if not self.use_fallback:
                raise

        if len(collected) < limit and self.use_fallback:
            fallback_items = MockDiscoveryScraper().discover_trending(hashtags=tags, limit=limit)
            for item in fallback_items:
                if item.url not in collected:
                    collected[item.url] = item
                if len(collected) >= limit:
                    break

        return list(collected.values())[:limit]
