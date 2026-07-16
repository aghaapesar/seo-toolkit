"""
HTTP page cache with ETag / Last-Modified support.

Input:
    URL and response headers/body from fetch.

Output:
    Cached HTML bytes or cache-hit metadata for conditional requests.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


def _url_key(url: str) -> str:
    """Return stable filename stem for a URL."""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]


@dataclass
class CacheEntry:
    """Cached page record."""

    url: str
    etag: Optional[str]
    last_modified: Optional[str]
    content_hash: str
    fetched_at: str
    html_path: str


class PageCache:
    """
    Disk cache for downloaded HTML pages.

    Stores raw HTML plus metadata JSON for conditional GET on re-runs.
    """

    def __init__(self, cache_dir: Path) -> None:
        """
        Initialize cache directory.

        Input:
            cache_dir: Folder for *.html and *.meta.json files.
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _meta_path(self, url: str) -> Path:
        """Return metadata JSON path for URL."""
        return self.cache_dir / f"{_url_key(url)}.meta.json"

    def _html_path(self, url: str) -> Path:
        """Return cached HTML path for URL."""
        return self.cache_dir / f"{_url_key(url)}.html"

    def load(self, url: str) -> Optional[CacheEntry]:
        """
        Load cache entry metadata if present.

        Output:
            CacheEntry or None when not cached.
        """
        meta_path = self._meta_path(url)
        if not meta_path.exists():
            return None
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            return CacheEntry(**data)
        except (json.JSONDecodeError, TypeError, OSError) as exc:
            logger.warning("Invalid cache meta for %s: %s", url, exc)
            return None

    def load_html(self, url: str) -> Optional[bytes]:
        """
        Load cached HTML bytes.

        Output:
            HTML bytes or None.
        """
        html_path = self._html_path(url)
        if not html_path.exists():
            return None
        try:
            return html_path.read_bytes()
        except OSError as exc:
            logger.warning("Cannot read cache HTML for %s: %s", url, exc)
            return None

    def conditional_headers(self, url: str) -> Dict[str, str]:
        """
        Build If-None-Match / If-Modified-Since headers from cache.

        Output:
            Headers dict (may be empty).
        """
        entry = self.load(url)
        if not entry:
            return {}
        headers: Dict[str, str] = {}
        if entry.etag:
            headers["If-None-Match"] = entry.etag
        if entry.last_modified:
            headers["If-Modified-Since"] = entry.last_modified
        return headers

    def save(
        self,
        url: str,
        html: bytes,
        etag: Optional[str] = None,
        last_modified: Optional[str] = None,
    ) -> CacheEntry:
        """
        Persist HTML and metadata to cache.

        Input:
            url: Source page URL.
            html: Raw response body.
            etag: Optional ETag header value.
            last_modified: Optional Last-Modified header value.

        Output:
            Saved CacheEntry record.
        """
        content_hash = hashlib.sha256(html).hexdigest()
        html_path = self._html_path(url)
        html_path.write_bytes(html)

        entry = CacheEntry(
            url=url,
            etag=etag,
            last_modified=last_modified,
            content_hash=content_hash,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            html_path=str(html_path),
        )
        self._meta_path(url).write_text(
            json.dumps(entry.__dict__, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return entry

    def is_unchanged(self, url: str, etag: Optional[str], last_modified: Optional[str]) -> bool:
        """
        Check whether response headers match cached entry.

        Output:
            True when server indicates page unchanged (304 scenario).
        """
        entry = self.load(url)
        if not entry:
            return False
        if etag and entry.etag and etag == entry.etag:
            return True
        if last_modified and entry.last_modified and last_modified == entry.last_modified:
            return True
        return False
