"""
Shared outbound HTTP client for sitemap downloads and scraping.

Input:
    URL and optional config.yaml app.http_proxy settings.

Output:
    Response bytes or structured error message.
"""

from __future__ import annotations

import logging
import os
import platform
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse

import requests
import yaml

logger = logging.getLogger(__name__)

DEFAULT_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/xml,text/xml,application/xhtml+xml,text/html;q=0.9,*/*;q=0.8",
    "Accept-Language": "fa-IR,fa;q=0.9,en-US,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}

_http_settings_cache: Optional[Dict] = None


def load_http_settings() -> Dict:
    """
    Load HTTP proxy settings from config.yaml app section.

    Output:
        Dict with http_proxy, https_proxy, trust_system_proxy keys.
    """
    global _http_settings_cache
    if _http_settings_cache is not None:
        return _http_settings_cache

    settings = {
        "http_proxy": "",
        "https_proxy": "",
        "trust_system_proxy": False,
    }
    config_path = Path("config.yaml")
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        app_cfg = data.get("app") or {}
        settings["http_proxy"] = (app_cfg.get("http_proxy") or "").strip()
        settings["https_proxy"] = (
            app_cfg.get("https_proxy") or app_cfg.get("http_proxy") or ""
        ).strip()
        settings["trust_system_proxy"] = bool(app_cfg.get("trust_system_proxy", False))

    _http_settings_cache = settings
    return settings


def build_http_session() -> requests.Session:
    """
    Build requests session with optional proxy from config.

    Output:
        Configured requests.Session (trust_env off by default).
    """
    settings = load_http_settings()
    session = requests.Session()
    session.trust_env = settings["trust_system_proxy"]

    proxies = {}
    if settings["http_proxy"]:
        proxies["http"] = settings["http_proxy"]
    if settings["https_proxy"]:
        proxies["https"] = settings["https_proxy"]
    if proxies:
        session.proxies.update(proxies)
    else:
        # Force direct connection — ignore IDE-injected HTTP_PROXY (e.g. Cursor sandbox).
        session.proxies.update({"http": None, "https": None})

    return session


def _clean_proxy_env() -> Dict[str, str]:
    """Return a copy of os.environ without proxy variables."""
    return {
        key: value
        for key, value in os.environ.items()
        if "proxy" not in key.lower()
    }


def _fetch_via_curl(url: str, timeout: int) -> Tuple[Optional[bytes], Optional[str]]:
    """
    macOS fallback: use system curl when requests cannot resolve/connect.

    Input:
        url: Target URL.
        timeout: Max seconds for curl --max-time.

    Output:
        Tuple of (body bytes, error message).
    """
    if platform.system() != "Darwin" or not shutil.which("curl"):
        return None, None

    try:
        proc = subprocess.run(
            [
                "curl",
                "-fsSL",
                "--max-time",
                str(timeout),
                "-A",
                DEFAULT_REQUEST_HEADERS["User-Agent"],
                "-H",
                f"Accept: {DEFAULT_REQUEST_HEADERS['Accept']}",
                url,
            ],
            capture_output=True,
            env=_clean_proxy_env(),
            timeout=timeout + 5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, f"curl fallback failed: {exc}"

    if proc.returncode == 0 and proc.stdout:
        logger.info("Fetched via curl fallback: %s (%s bytes)", url, len(proc.stdout))
        return proc.stdout, None

    stderr = (proc.stderr or b"").decode("utf-8", errors="replace").strip()
    return None, stderr or f"curl exit code {proc.returncode}"


def fetch_url(
    url: str,
    timeout: int = 45,
    max_retries: int = 3,
) -> Tuple[Optional[bytes], Optional[str]]:
    """
    Download URL with browser-like headers and optional HTTPS→HTTP fallback.

    Input:
        url: Target URL.
        timeout: Request timeout seconds.
        max_retries: Retries per URL variant.

    Output:
        Tuple of (content bytes, error message).
    """
    url = url.strip()
    if not url:
        return None, "URL is empty"

    parsed = urlparse(url)
    referer = f"{parsed.scheme}://{parsed.netloc}/"
    headers = {**DEFAULT_REQUEST_HEADERS, "Referer": referer}

    session = build_http_session()
    candidates = [url]
    if url.startswith("https://"):
        candidates.append(url.replace("https://", "http://", 1))

    last_error: Optional[str] = None

    for candidate in candidates:
        for attempt in range(1, max_retries + 1):
            try:
                response = session.get(
                    candidate,
                    headers=headers,
                    timeout=timeout,
                    allow_redirects=True,
                )
                response.raise_for_status()
                logger.info("Fetched %s (%s bytes)", candidate, len(response.content))
                return response.content, None
            except requests.RequestException as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                logger.warning(
                    "Fetch attempt %s/%s failed for %s: %s",
                    attempt,
                    max_retries,
                    candidate,
                    last_error,
                )
                if attempt < max_retries:
                    time.sleep(min(2 ** attempt, 10))

    # macOS: curl often works when Python requests fails (IDE proxy/DNS env).
    curl_content, curl_error = _fetch_via_curl(url, timeout=timeout)
    if curl_content:
        return curl_content, None
    if curl_error:
        last_error = curl_error

    hint = (
        " If the site opens in your browser but not here, upload sitemap.xml manually "
        "or set app.http_proxy in config.yaml."
    )
    return None, (last_error or "Request failed") + hint


def reset_http_settings_cache() -> None:
    """Clear cached HTTP settings (for tests)."""
    global _http_settings_cache
    _http_settings_cache = None
