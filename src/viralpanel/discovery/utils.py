import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def netscape_to_patchright_storage(cookies_txt_path: str | Path | None) -> dict[str, list[Any]]:
    """Converte um arquivo cookies.txt (formato Netscape do yt-dlp) ou .json para o formato storage_state do Playwright/Patchright."""
    empty_state: dict[str, list[Any]] = {"cookies": [], "origins": []}
    if not cookies_txt_path:
        return empty_state

    path = Path(cookies_txt_path)
    if not path.exists() or not path.is_file():
        return empty_state

    try:
        raw_content = path.read_text(encoding="utf-8", errors="ignore").strip()
    except Exception as exc:
        logger.warning("Falha ao ler arquivo de cookies %s: %s", path, exc)
        return empty_state

    if not raw_content:
        return empty_state

    # Caso 1: Arquivo JSON (storage_state ou lista de cookies exportados de extensão)
    if path.suffix.lower() == ".json" or raw_content.startswith(("{", "[")):
        try:
            data = json.loads(raw_content)
            if isinstance(data, dict) and "cookies" in data:
                return {
                    "cookies": list(data.get("cookies") or []),
                    "origins": list(data.get("origins") or []),
                }
            if isinstance(data, list):
                normalized_cookies = []
                for c in data:
                    if isinstance(c, dict) and "name" in c and "value" in c and "domain" in c:
                        same_site = str(c.get("sameSite", "Lax")).capitalize()
                        if same_site not in ("Strict", "Lax", "None"):
                            same_site = "Lax"
                        normalized_cookies.append(
                            {
                                "name": str(c["name"]),
                                "value": str(c["value"]),
                                "domain": str(c["domain"]),
                                "path": str(c.get("path") or "/"),
                                "expires": float(c.get("expirationDate") or c.get("expires") or -1),
                                "httpOnly": bool(c.get("httpOnly", False)),
                                "secure": bool(c.get("secure", True)),
                                "sameSite": same_site,
                            }
                        )
                return {"cookies": normalized_cookies, "origins": []}
        except Exception as exc:
            logger.warning("Falha ao parsear JSON de cookies %s: %s", path, exc)
            return empty_state

    # Caso 2: Formato Netscape HTTP Cookie File (7 colunas separadas por TAB)
    cookies: list[dict[str, Any]] = []
    for line in raw_content.splitlines():
        line = line.strip()
        if not line:
            continue

        http_only = False
        if line.startswith("#HttpOnly_"):
            http_only = True
            line = line[len("#HttpOnly_") :]
        elif line.startswith("#"):
            continue

        parts = line.split("\t")
        if len(parts) < 7:
            continue

        domain, _include_subdomains, cookie_path, secure_str, expires_str, name, value = parts[:7]
        try:
            expires_val = float(expires_str) if expires_str and int(float(expires_str)) > 0 else -1.0
        except ValueError:
            expires_val = -1.0

        cookies.append(
            {
                "name": name,
                "value": value,
                "domain": domain,
                "path": cookie_path or "/",
                "expires": expires_val,
                "httpOnly": http_only,
                "secure": secure_str.upper() == "TRUE",
                "sameSite": "Lax",
            }
        )

    return {"cookies": cookies, "origins": []}

