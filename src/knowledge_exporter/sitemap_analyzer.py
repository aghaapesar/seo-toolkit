"""
Sitemap segment analysis — URL pattern grouping + live page sampling.

Input:
    Root sitemap URL.

Output:
    Segments keyed by URL path pattern with content type from sampled pages.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from src.services.http_client import fetch_url
from src.site_page_extractor import _detect_page_type, _parse_json_ld_blocks
from web.app.services.sitemap_fetch import fetch_all_sitemap_urls, normalize_sitemap_url

logger = logging.getLogger(__name__)

_LOCALE_RE = re.compile(r"^[a-z]{2}(-[a-z]{2})?$", re.I)
_NUMERIC_RE = re.compile(r"^\d+$")

CONTENT_TYPE_LABELS = {
    "product": ("Products", "محصولات"),
    "category": ("Categories", "دسته‌بندی‌ها"),
    "blog": ("Blog / articles", "بلاگ / مقالات"),
    "other": ("Other / general", "سایر / عمومی"),
}

# First path segment treated as listing container (deeper segment is slug/id)
_LISTING_SEGMENTS = frozenset(
    {
        "product",
        "products",
        "p",
        "blog",
        "post",
        "posts",
        "article",
        "articles",
        "news",
        "tag",
        "tags",
        "page",
        "pages",
        "shop",
        "item",
        "items",
        "محصول",
        "مقاله",
        "وبلاگ",
    }
)

# Two-level structural prefixes (pattern uses two fixed segments)
_TWO_LEVEL_PREFIXES = frozenset(
    {
        "product-category",
        "product-cat",
        "product_cat",
        "product-tag",
        "blog-category",
        "blog-cat",
    }
)


def _dedupe_urls(urls: List[str]) -> List[str]:
    """Return unique URLs preserving first-seen order."""
    seen: set[str] = set()
    out: List[str] = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            out.append(url)
    return out


def _path_parts(url: str) -> List[str]:
    """
    Split URL path into segments, skipping locale prefix when present.

    Output:
        Non-empty path segments without locale code.
    """
    parts = [p for p in urlparse(url).path.split("/") if p]
    if parts and _LOCALE_RE.match(parts[0]):
        parts = parts[1:]
    return parts


def extract_url_pattern(url: str) -> str:
    """
    Derive a stable URL path pattern for segment grouping.

    Examples:
        /product/game-a  → /product/*
        /fa/blog/post-1  → /blog/*
        /product-category/toys/item  → /product-category/toys/*
        /about  → /about/

    Output:
        Pattern string used as segment key.
    """
    parts = _path_parts(url)
    if not parts:
        return "/"

    if len(parts) == 1:
        return f"/{parts[0]}/"

    first = parts[0].lower()
    second = parts[1].lower() if len(parts) > 1 else ""

    if first in _TWO_LEVEL_PREFIXES and len(parts) >= 2:
        if len(parts) == 2:
            return f"/{parts[0]}/{parts[1]}/"
        return f"/{parts[0]}/{parts[1]}/*"

    if first in _LISTING_SEGMENTS or _looks_like_slug(second):
        return f"/{parts[0]}/*"

    if len(parts) >= 2 and not _looks_like_slug(first):
        return f"/{parts[0]}/{parts[1]}/"

    return f"/{parts[0]}/*"


def _looks_like_slug(segment: str) -> bool:
    """Heuristic: segment is likely a product/post slug or numeric id."""
    if not segment:
        return False
    if _NUMERIC_RE.match(segment):
        return True
    if len(segment) > 24:
        return True
    if "-" in segment or "_" in segment:
        return True
    return False


def group_urls_by_pattern(urls: List[str]) -> Dict[str, List[str]]:
    """
    Group sitemap URLs by extracted path pattern.

    Output:
        Map pattern → URL list (deduped per pattern).
    """
    grouped: Dict[str, List[str]] = {}
    for page_url in urls:
        pattern = extract_url_pattern(page_url)
        grouped.setdefault(pattern, []).append(page_url)
    return grouped


def _page_title(soup: BeautifulSoup) -> str:
    """Extract document title from HTML soup."""
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        return str(og["content"]).strip()
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(" ", strip=True)
    return ""


def analyze_single_page(url: str, *, timeout: int = 30, max_retries: int = 2) -> Dict[str, Any]:
    """
    Fetch one page and detect content type from JSON-LD + path.

    Output:
        Dict with url, status, content_type, title, error.
    """
    html, error = fetch_url(url, timeout=timeout, max_retries=max_retries)
    if not html:
        return {
            "url": url,
            "status": "failed",
            "content_type": "other",
            "title": "",
            "error": error or "fetch failed",
        }
    try:
        decoded = html.decode("utf-8", errors="replace")
        soup = BeautifulSoup(decoded, "lxml")
        ld_items = _parse_json_ld_blocks(soup)
        content_type = _detect_page_type(url, ld_items)
        title = _page_title(soup)
        return {
            "url": url,
            "status": "success",
            "content_type": content_type,
            "title": title,
            "error": None,
        }
    except Exception as exc:
        logger.warning("Sample analyze failed for %s: %s", url, exc)
        return {
            "url": url,
            "status": "failed",
            "content_type": "other",
            "title": "",
            "error": str(exc),
        }


def _pick_sample_urls(urls: List[str], sample_size: int) -> List[str]:
    """
    Pick evenly spaced sample URLs from a pattern group.

    Output:
        Up to sample_size URLs.
    """
    if len(urls) <= sample_size:
        return list(urls)
    if sample_size <= 1:
        return [urls[0]]
    step = max(1, len(urls) // sample_size)
    picked: List[str] = []
    for idx in range(0, len(urls), step):
        picked.append(urls[idx])
        if len(picked) >= sample_size:
            break
    return picked


def _majority_content_type(samples: List[Dict[str, Any]]) -> Tuple[str, str]:
    """
    Vote content type from successful samples.

    Output:
        Tuple of (content_type, confidence label e.g. '2/3').
    """
    ok = [s for s in samples if s.get("status") == "success"]
    if not ok:
        return "other", f"0/{len(samples)}"
    counts = Counter(s["content_type"] for s in ok)
    winner, count = counts.most_common(1)[0]
    return winner, f"{count}/{len(samples)}"


def analyze_pattern_samples(
    pattern_urls: Dict[str, List[str]],
    *,
    samples_per_pattern: int = 3,
    timeout: int = 30,
    max_retries: int = 2,
    max_workers: int = 6,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Fetch and analyze sample pages for each URL pattern.

    Input:
        pattern_urls: Pattern → full URL list.

    Output:
        Pattern → list of sample analysis dicts.
    """
    tasks: List[Tuple[str, str]] = []
    for pattern, urls in pattern_urls.items():
        for sample_url in _pick_sample_urls(urls, samples_per_pattern):
            tasks.append((pattern, sample_url))

    results: Dict[str, List[Dict[str, Any]]] = {p: [] for p in pattern_urls}
    if not tasks:
        return results

    with ThreadPoolExecutor(max_workers=max(1, max_workers)) as pool:
        future_map = {
            pool.submit(
                analyze_single_page,
                sample_url,
                timeout=timeout,
                max_retries=max_retries,
            ): (pattern, sample_url)
            for pattern, sample_url in tasks
        }
        for future in as_completed(future_map):
            pattern, _url = future_map[future]
            try:
                results[pattern].append(future.result())
            except Exception as exc:
                results[pattern].append(
                    {
                        "url": _url,
                        "status": "failed",
                        "content_type": "other",
                        "title": "",
                        "error": str(exc),
                    }
                )
    return results


def _segment_id(pattern: str) -> str:
    """Build stable segment id from URL pattern."""
    digest = hashlib.sha256(pattern.encode("utf-8")).hexdigest()[:10]
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", pattern)[:48]
    return f"pattern:{safe}:{digest}"


def build_pattern_segments(
    pattern_urls: Dict[str, List[str]],
    sample_results: Dict[str, List[Dict[str, Any]]],
) -> Tuple[List[Dict[str, Any]], Dict[str, List[str]]]:
    """
    Build UI segments from URL patterns and sample analysis.

    Output:
        Tuple of (segment metadata list, segment_id → URLs map).
    """
    segments: List[Dict[str, Any]] = []
    segment_urls: Dict[str, List[str]] = {}

    for pattern, urls in sorted(pattern_urls.items(), key=lambda x: -len(x[1])):
        if not urls:
            continue
        samples = sample_results.get(pattern) or []
        content_type, confidence = _majority_content_type(samples)
        label_en, label_fa = CONTENT_TYPE_LABELS.get(content_type, (content_type, content_type))

        seg_id = _segment_id(pattern)
        pattern_label = pattern if pattern != "/" else "/ (home & root)"

        segments.append(
            {
                "id": seg_id,
                "group": "url_pattern",
                "group_label_en": "URL pattern",
                "group_label_fa": "پترن URL",
                "url_pattern": pattern,
                "label": pattern_label,
                "label_fa": pattern_label,
                "content_type": content_type,
                "content_type_label_en": label_en,
                "content_type_label_fa": label_fa,
                "sample_confidence": confidence,
                "count": len(urls),
                "sample_urls": urls[:5],
                "sample_pages": [
                    {
                        "url": s.get("url"),
                        "title": s.get("title") or "",
                        "content_type": s.get("content_type"),
                        "status": s.get("status"),
                    }
                    for s in samples
                ],
            }
        )
        segment_urls[seg_id] = list(urls)

    return segments, segment_urls


def analyze_sitemap(
    sitemap_url: str,
    *,
    max_retries: int = 5,
    timeout: int = 45,
    samples_per_pattern: int = 3,
    sample_timeout: int = 30,
    sample_workers: int = 6,
) -> Dict[str, Any]:
    """
    Analyze sitemap: group by URL pattern, sample pages, infer content types.

    Output:
        Analysis dict with pattern-based segments.
    """
    url = normalize_sitemap_url(sitemap_url)
    if not url:
        raise ValueError("Sitemap URL is required")

    all_urls, error, sources = fetch_all_sitemap_urls(
        url,
        max_retries=max_retries,
        timeout=timeout,
    )
    all_urls = _dedupe_urls(all_urls)
    if not all_urls:
        raise ValueError(error or "No URLs found in sitemap")

    pattern_urls = group_urls_by_pattern(all_urls)
    sample_results = analyze_pattern_samples(
        pattern_urls,
        samples_per_pattern=max(1, min(samples_per_pattern, 5)),
        timeout=sample_timeout,
        max_retries=min(max_retries, 3),
        max_workers=sample_workers,
    )
    segments, segment_urls = build_pattern_segments(pattern_urls, sample_results)

    analysis_id = uuid.uuid4().hex
    warnings: List[str] = []
    if error:
        warnings.append(error)

    failed_samples = sum(
        1 for samples in sample_results.values() for s in samples if s.get("status") != "success"
    )
    if failed_samples:
        warnings.append(f"{failed_samples} sample page fetches failed (export may still proceed)")

    return {
        "analysis_id": analysis_id,
        "sitemap_url": url,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_urls": len(all_urls),
        "pattern_count": len(segments),
        "sitemap_sources": sources,
        "segments": segments,
        "segment_urls": segment_urls,
        "all_urls": all_urls,
        "warnings": warnings,
    }


def resolve_selected_urls(analysis: Dict[str, Any], selected_segment_ids: List[str]) -> List[str]:
    """
    Union URLs from selected pattern segments (deduped).

    Output:
        URL list to export.
    """
    if not selected_segment_ids:
        return list(analysis.get("all_urls") or [])

    segment_urls: Dict[str, List[str]] = analysis.get("segment_urls") or {}
    merged: List[str] = []
    seen: set[str] = set()
    for seg_id in selected_segment_ids:
        for page_url in segment_urls.get(seg_id, []):
            if page_url not in seen:
                seen.add(page_url)
                merged.append(page_url)
    return merged


def save_analysis(cache_dir: Path, analysis: Dict[str, Any]) -> Path:
    """Persist analysis JSON to disk."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"{analysis['analysis_id']}.json"
    path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_analysis(cache_dir: Path, analysis_id: str) -> Optional[Dict[str, Any]]:
    """Load saved analysis by id."""
    path = cache_dir / f"{analysis_id}.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
