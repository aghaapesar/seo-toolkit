"""
Page fetcher with cache, retries, and conditional GET.

Input:
    URL and KnowledgeExporterConfig fetch settings.

Output:
    HTML bytes or error message.
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass
from typing import Optional, Tuple

import requests

from src.services.http_client import DEFAULT_REQUEST_HEADERS, build_http_session
from src.knowledge_exporter.page_cache import PageCache

logger = logging.getLogger(__name__)


@dataclass
class FetchResult:
    """Result of fetching one URL."""

    url: str
    html: Optional[bytes]
    from_cache: bool
    etag: Optional[str] = None
    last_modified: Optional[str] = None
    error: Optional[str] = None


class PageFetcher:
    """
    HTTP fetcher with disk cache and retry logic.
    """

    def __init__(
        self,
        cache: PageCache,
        timeout: int = 45,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize fetcher.

        Input:
            cache: PageCache instance.
            timeout: Request timeout seconds.
            max_retries: Retry attempts per URL.
        """
        self.cache = cache
        self.timeout = timeout
        self.max_retries = max_retries
        self._session = build_http_session()

    def fetch(self, url: str) -> FetchResult:
        """
        Fetch URL with cache and conditional headers.

        Output:
            FetchResult with HTML or error.
        """
        conditional = self.cache.conditional_headers(url)
        headers = {**DEFAULT_REQUEST_HEADERS, **conditional}

        last_error: Optional[str] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self._session.get(
                    url,
                    headers=headers,
                    timeout=self.timeout,
                    allow_redirects=True,
                )
                if response.status_code == 304:
                    cached = self.cache.load_html(url)
                    if cached:
                        return FetchResult(url=url, html=cached, from_cache=True)
                    last_error = "304 Not Modified but cache missing"
                    break

                response.raise_for_status()
                html = response.content
                etag = response.headers.get("ETag")
                last_mod = response.headers.get("Last-Modified")
                self.cache.save(url, html, etag=etag, last_modified=last_mod)
                return FetchResult(
                    url=url,
                    html=html,
                    from_cache=False,
                    etag=etag,
                    last_modified=last_mod,
                )
            except requests.RequestException as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                logger.warning("Fetch %s attempt %d/%d: %s", url, attempt, self.max_retries, last_error)
                if attempt < self.max_retries:
                    time.sleep(min(2 ** attempt, 8))

        # Fallback to stale cache on failure
        cached = self.cache.load_html(url)
        if cached:
            logger.info("Using stale cache for %s after fetch failure", url)
            return FetchResult(url=url, html=cached, from_cache=True, error=last_error)

        return FetchResult(url=url, html=None, from_cache=False, error=last_error or "Fetch failed")


def content_hash(text: str) -> str:
    """Return SHA-256 hex digest of normalized text."""
    normalized = " ".join(text.split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
