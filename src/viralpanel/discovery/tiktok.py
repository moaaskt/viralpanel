import json
import logging
import os
import re
import subprocess
from datetime import datetime, timedelta, timezone
from typing import Any

from viralpanel.config import get_settings
from viralpanel.discovery.base import BaseScraper, ScrapedVideoMetadata

logger = logging.getLogger(__name__)


class MockDiscoveryScraper(BaseScraper):
    """Gerador determinístico de 30 vídeos de desenvolvimento pessoal para fallback e testes."""

    def __init__(self, base_now: datetime | None = None):
        self.base_now = base_now or datetime.now(timezone.utc)

    def discover_trending(
        self,
        hashtags: list[str] | None = None,
        limit: int = 30,
        seed_accounts: list[str] | None = None,
        search_queries: list[str] | None = None,
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
    """Scraper robusto do TikTok em camadas:

    Camada 1: Playwright Chromium com network interception de JSONs de busca/tag e rehydration tags.
    Camada 2: yt-dlp via Seed Profiles e busca direta por hashtag/termos.
    Zero fallback para mocks se use_fallback=False.
    """

    def __init__(
        self,
        use_fallback: bool = False,
        timeout_seconds: int = 40,
        cookies_path: str | None = None,
    ):
        self.use_fallback = use_fallback
        self.timeout_seconds = timeout_seconds
        settings = get_settings()
        self.cookies_path = cookies_path or settings.tiktok_cookies_path

    # =========================================================================
    # Helpers de Normalização de Vídeo TikTok
    # =========================================================================
    def _parse_tiktok_item_dict(self, item: dict[str, Any], tag_or_query: str) -> ScrapedVideoMetadata | None:
        try:
            video_id = str(item.get("id") or item.get("videoId") or "")
            if not video_id:
                return None

            author_obj = item.get("author") or {}
            author = ""
            if isinstance(author_obj, dict):
                author = author_obj.get("uniqueId") or author_obj.get("nickname") or ""
            elif isinstance(author_obj, str):
                author = author_obj

            if not author:
                author = "unknown"

            stats = item.get("stats") or item.get("statsV2") or {}
            views = int(stats.get("playCount") or stats.get("viewCount") or 0)
            likes = int(stats.get("diggCount") or stats.get("likeCount") or 0)
            comments = int(stats.get("commentCount") or 0)
            shares = int(stats.get("shareCount") or stats.get("repostCount") or 0)

            create_time = item.get("createTime") or item.get("createdAt")
            if create_time:
                posted_at = datetime.fromtimestamp(int(create_time), tz=timezone.utc)
            else:
                posted_at = datetime.now(timezone.utc)

            desc = item.get("desc") or item.get("title") or ""
            video_url = f"https://www.tiktok.com/@{author}/video/{video_id}"

            # Extrair hashtags do desc ou usar tag_or_query
            found_tags = re.findall(r"#(\w+)", desc)
            if not found_tags and tag_or_query:
                found_tags = [tag_or_query.replace("#", "")]

            return ScrapedVideoMetadata(
                url=video_url,
                platform="tiktok",
                author=author,
                title=desc,
                views=views,
                likes=likes,
                comments=comments,
                shares=shares,
                posted_at=posted_at,
                hashtags=found_tags,
            )
        except Exception as exc:
            logger.debug("Falha ao parsear item TikTok: %s", exc)
            return None

    # =========================================================================
    # Camada 1: Playwright com Network Interception & Rehydration Script Tags
    # =========================================================================
    def _collect_via_playwright(
        self,
        search_terms: list[str],
        limit: int,
    ) -> list[ScrapedVideoMetadata]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.warning("Playwright não instalado no ambiente. Pulando camada 1.")
            return []

        collected: dict[str, ScrapedVideoMetadata] = {}

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-blink-features=AutomationControlled",
                    ],
                )
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1280, "height": 800},
                    locale="pt-BR",
                )

                page = context.new_page()

                def handle_response(response):
                    url = response.url
                    # Intercepta rotas de API do TikTok
                    if any(endpoint in url for endpoint in ["/api/search/", "/api/challenge/item_list/", "/api/post/item_list/"]):
                        try:
                            data = response.json()
                            items = []
                            if "data" in data and isinstance(data["data"], list):
                                for d in data["data"]:
                                    if "item" in d:
                                        items.append(d["item"])
                                    else:
                                        items.append(d)
                            elif "itemList" in data and isinstance(data["itemList"], list):
                                items = data["itemList"]

                            for raw_item in items:
                                parsed = self._parse_tiktok_item_dict(raw_item, "")
                                if parsed and parsed.url not in collected:
                                    collected[parsed.url] = parsed
                        except Exception:
                            pass

                page.on("response", handle_response)

                for term in search_terms:
                    if len(collected) >= limit:
                        break

                    url = f"https://www.tiktok.com/tag/{term}" if not term.startswith("search:") else f"https://www.tiktok.com/search?q={term[7:]}"
                    try:
                        page.goto(url, timeout=self.timeout_seconds * 1000, wait_until="domcontentloaded")
                        page.wait_for_timeout(3000)

                        # Verifica hydration script tags
                        content = page.content()
                        # Procura scripts universais de hydration
                        for match in re.finditer(r'<script id="(?:__UNIVERSAL_DATA_FOR_REHYDRATION__|SIGI_STATE)"[^>]*>(\{.*?\})</script>', content):
                            try:
                                json_data = json.loads(match.group(1))
                                # Varre chaves recursivamente ou dicionário ItemModule
                                items_dict = (
                                    json_data.get("__DEFAULT_SCOPE__", {})
                                    .get("webapp.video-detail", {})
                                    .get("itemInfo", {})
                                    .get("itemStruct")
                                )
                                if items_dict:
                                    parsed = self._parse_tiktok_item_dict(items_dict, term)
                                    if parsed:
                                        collected[parsed.url] = parsed

                                item_module = json_data.get("ItemModule", {})
                                for itm in item_module.values():
                                    parsed = self._parse_tiktok_item_dict(itm, term)
                                    if parsed:
                                        collected[parsed.url] = parsed
                            except Exception:
                                pass

                        # Scroll leve para forçar disparo de requisição de mais itens
                        page.mouse.wheel(0, 1000)
                        page.wait_for_timeout(2000)

                    except Exception as err:
                        logger.debug("Playwright aviso ao navegar em %s: %s", url, err)

                browser.close()
        except Exception as exc:
            logger.warning("Falha durante execução do Playwright no TikTok: %s", exc)

        return list(collected.values())

    # =========================================================================
    # Camada 2: yt-dlp via Seed Profiles & Hashtag dump
    # =========================================================================
    def _collect_via_ytdlp(
        self,
        targets: list[str],
        max_items_per_target: int,
    ) -> list[ScrapedVideoMetadata]:
        if shutil_which := subprocess.run(["which", "yt-dlp"], capture_output=True, text=True).returncode != 0:
            logger.warning("yt-dlp não disponível no PATH.")
            return []

        results: list[ScrapedVideoMetadata] = []

        for target in targets:
            if target.startswith("http"):
                url = target
                tag_or_acc = target.split("@")[-1].split("/")[0] if "@" in target else target
            elif target.startswith("@") or not target.startswith("#"):
                clean_acc = target.lstrip("@")
                url = f"https://www.tiktok.com/@{clean_acc}"
                tag_or_acc = clean_acc
            else:
                clean_tag = target.lstrip("#")
                url = f"https://www.tiktok.com/tag/{clean_tag}"
                tag_or_acc = clean_tag

            cmd = [
                "yt-dlp",
                "--flat-playlist",
                "--dump-json",
                "--playlist-end", str(max_items_per_target),
                "--no-playlist",
                "--geo-bypass",
                "--user-agent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            ]

            if self.cookies_path and os.path.exists(self.cookies_path):
                cmd.extend(["--cookies", str(self.cookies_path)])

            cmd.append(url)

            try:
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    check=False,
                )
                for line in proc.stdout.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    video_url = data.get("webpage_url") or data.get("url")
                    if not video_url:
                        continue

                    # yt-dlp flat playlist pode retornar apenas video id na url
                    if not video_url.startswith("http"):
                        video_url = f"https://www.tiktok.com/video/{video_url}"

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
                            author=data.get("uploader") or data.get("creator") or data.get("channel") or tag_or_acc,
                            title=data.get("title") or data.get("description") or "",
                            views=int(data.get("view_count") or 0),
                            likes=int(data.get("like_count") or 0),
                            comments=int(data.get("comment_count") or 0),
                            shares=int(data.get("repost_count") or 0),
                            posted_at=posted_at,
                            hashtags=[tag_or_acc],
                        )
                    )
            except Exception as exc:
                logger.debug("Erro yt-dlp para target %s: %s", target, exc)

        return results

    # =========================================================================
    # Interface pública: discover_trending
    # =========================================================================
    def discover_trending(
        self,
        hashtags: list[str] | None = None,
        limit: int = 30,
        seed_accounts: list[str] | None = None,
        search_queries: list[str] | None = None,
    ) -> list[ScrapedVideoMetadata]:
        tags = hashtags or ["desenvolvimentopessoal", "motivacao", "disciplina"]
        seeds = seed_accounts or [
            "eslen.delanogare",
            "reservatorio.de.dopamina",
            "wendellcarvalho",
            "flavioaugustodasilva",
            "joeljota",
        ]
        queries = search_queries or ["desenvolvimento pessoal", "disciplina e foco"]

        collected: dict[str, ScrapedVideoMetadata] = {}

        # 1. Camada 1: Playwright Network Interception nos termos e tags
        logger.info("TikTokDiscovery: Iniciando Camada 1 (Playwright Chromium)...")
        pw_search_terms = tags[:3] + [f"search:{q}" for q in queries[:2]]
        pw_results = self._collect_via_playwright(pw_search_terms, limit=limit)
        for v in pw_results:
            collected[v.url] = v

        logger.info("TikTokDiscovery: Camada 1 coletou %d vídeos.", len(collected))

        # 2. Camada 2: yt-dlp via Seed Profiles e Hashtags se ainda faltar para o limite
        if len(collected) < limit:
            remaining = limit - len(collected)
            logger.info("TikTokDiscovery: Iniciando Camada 2 (yt-dlp Seed Profiles / Tags) para coletar mais %d...", remaining)
            targets = seeds + tags
            per_target = max(remaining // max(len(targets), 1), 5)
            ytdlp_results = self._collect_via_ytdlp(targets, max_items_per_target=per_target)
            for v in ytdlp_results:
                if v.url not in collected:
                    collected[v.url] = v
                if len(collected) >= limit:
                    break
            logger.info("TikTokDiscovery: Total após Camada 2: %d vídeos.", len(collected))

        # Se mesmo com as duas camadas não atingir ou falhar e fallback estiver desabilitado:
        if len(collected) == 0 and not self.use_fallback:
            raise RuntimeError(
                "Nenhum vídeo pôde ser coletado no TikTok (Playwright e yt-dlp falharam ou foram bloqueados) "
                "e use_fallback=False. Forneça cookies válidos via TIKTOK_COOKIES_PATH ou verifique a conexão."
            )

        # Fallback para mocks apenas se explicitamente habilitado (testes / simulação)
        if len(collected) < limit and self.use_fallback:
            logger.warning("TikTokDiscovery: Ativando fallback MockDiscoveryScraper para preencher %d vídeos.", limit - len(collected))
            mock_items = MockDiscoveryScraper().discover_trending(hashtags=tags, limit=limit)
            for item in mock_items:
                if item.url not in collected:
                    collected[item.url] = item
                if len(collected) >= limit:
                    break

        return list(collected.values())[:limit]
