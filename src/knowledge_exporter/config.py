"""
Configuration for knowledge_exporter module.

Input:
    CLI arguments or programmatic KnowledgeExporterConfig fields.

Output:
    Validated settings for crawl, extract, and Markdown part writing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Pattern


@dataclass
class KnowledgeExporterConfig:
    """
    Settings for sitemap → RAG Markdown export.

    Attributes:
        output_dir: Directory for knowledge_part_*.md and index.json.
        sitemap_url: Root sitemap URL (optional if urls provided).
        urls: Pre-built URL list (skips sitemap fetch when non-empty).
        max_part_bytes: Max bytes per part file (default 500 KB).
        max_pages_per_part: Max documents per part file (default 50).
        include_pattern: Optional regex; URL must match when set.
        exclude_pattern: Optional regex; matching URLs are skipped.
        concurrency: Parallel fetch workers.
        rate_limit_seconds: Delay between starting new requests.
        timeout: HTTP timeout per request (seconds).
        max_retries: Retry count per URL.
        min_content_chars: Warn/skip threshold for very short pages.
        cache_dir: Page cache directory (defaults to output_dir/.cache).
        use_llm: Run LLM structuring step (requires model).
        model_name: AIModelManager model name for LLM step.
        include_blog: Include blog content type segments.
        include_noindex: Include pages with noindex meta.
        product_sample_limit: Max product URLs (0 = unlimited).
        write_parts: Write multi-product knowledge_part_*.md (primary output).
        write_per_url: Also write one pages/{type}/{slug}.md per URL (optional).
        skip_unchanged: Skip URLs when lastmod + content hash match registry.
        url_page_types: Optional URL → page_type map from sitemap analysis.
        lastmod_map: Optional URL → sitemap lastmod map.
        project_slug: Project slug for SQLite registry updates.
    """

    output_dir: Path
    sitemap_url: str = ""
    urls: List[str] = field(default_factory=list)
    max_part_bytes: int = 500 * 1024
    max_pages_per_part: int = 50
    include_pattern: Optional[str] = None
    exclude_pattern: Optional[str] = None
    concurrency: int = 4
    rate_limit_seconds: float = 0.25
    timeout: int = 45
    max_retries: int = 3
    min_content_chars: int = 100
    cache_dir: Optional[Path] = None
    use_llm: bool = True
    model_name: str = ""
    include_blog: bool = False
    include_noindex: bool = False
    product_sample_limit: int = 0
    write_parts: bool = True
    write_per_url: bool = False
    skip_unchanged: bool = True
    url_page_types: Optional[dict] = field(default=None, repr=False)
    lastmod_map: Optional[dict] = field(default=None, repr=False)
    project_slug: str = ""

    _include_re: Optional[Pattern[str]] = field(default=None, repr=False, compare=False)
    _exclude_re: Optional[Pattern[str]] = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Normalize paths and compile URL filter regexes."""
        self.output_dir = Path(self.output_dir)
        if self.cache_dir is None:
            self.cache_dir = self.output_dir / ".cache"
        else:
            self.cache_dir = Path(self.cache_dir)

        if self.include_pattern:
            self._include_re = re.compile(self.include_pattern)
        if self.exclude_pattern:
            self._exclude_re = re.compile(self.exclude_pattern)

    def url_allowed(self, url: str) -> bool:
        """
        Check URL against include/exclude regex filters.

        Input:
            url: Page URL string.

        Output:
            True when URL should be crawled.
        """
        if self._include_re and not self._include_re.search(url):
            return False
        if self._exclude_re and self._exclude_re.search(url):
            return False
        return True
