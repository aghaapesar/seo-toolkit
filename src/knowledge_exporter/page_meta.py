"""
Page metadata helpers for RAG export — slug, noindex, page type.

Input:
    URL and raw HTML bytes.

Output:
    Filesystem-safe slug, noindex flag, normalized page type.
"""

from __future__ import annotations

import hashlib
import re
from typing import Optional
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup

from src.site_page_extractor import _detect_page_type, _parse_json_ld_blocks

_SLUG_SAFE_RE = re.compile(r"[^a-z0-9\u0600-\u06ff\-]+", re.I)
_LOCALE_RE = re.compile(r"^[a-z]{2}(-[a-z]{2})?$", re.I)


def url_to_slug(url: str, *, max_len: int = 80) -> str:
    """
    Build filesystem slug from URL path (last meaningful segment).

    Output:
        Safe slug string; falls back to short hash when path is empty.
    """
    path = unquote(urlparse(url).path or "").strip("/")
    parts = [p for p in path.split("/") if p]
    if parts and _LOCALE_RE.match(parts[0]):
        parts = parts[1:]
    raw = parts[-1] if parts else hashlib.sha256(url.encode()).hexdigest()[:10]
    slug = _SLUG_SAFE_RE.sub("-", raw.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    if not slug:
        slug = hashlib.sha256(url.encode()).hexdigest()[:12]
    return slug[:max_len]


def detect_noindex(html: bytes) -> bool:
    """
    Detect noindex from meta robots or X-Robots-Tag in HTML.

    Output:
        True when page should be excluded from export (default policy).
    """
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception:
        return False

    for meta in soup.find_all("meta"):
        name = (meta.get("name") or meta.get("property") or "").lower()
        if "robots" not in name:
            continue
        content = (meta.get("content") or "").lower()
        if "noindex" in content:
            return True
    return False


def detect_page_type_from_html(html: bytes, url: str) -> str:
    """
    Infer page type from JSON-LD and URL path.

    Output:
        product | category | blog | other
    """
    try:
        soup = BeautifulSoup(html, "html.parser")
        blocks = _parse_json_ld_blocks(soup)
        return _detect_page_type(url, blocks)
    except Exception:
        return "other"


def normalize_page_type(value: Optional[str]) -> str:
    """Map unknown types to other."""
    v = (value or "other").strip().lower()
    if v in ("product", "category", "blog", "other"):
        return v
    return "other"
