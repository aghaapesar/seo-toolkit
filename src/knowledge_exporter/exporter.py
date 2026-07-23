"""
Knowledge Exporter orchestrator: sitemap → RAG Markdown parts.

Input:
    KnowledgeExporterConfig with sitemap URL or URL list.

Output:
    knowledge_part_*.md, index.json, and ExportSummary report.

Example:
    python -m src.knowledge_exporter \\
        --sitemap https://example.com/sitemap.xml \\
        --output output/knowledge_export
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from tqdm import tqdm

from web.app.services.sitemap_fetch import fetch_all_sitemap_urls
from src.knowledge_exporter.config import KnowledgeExporterConfig
from src.knowledge_exporter.content_extractor import (
    ExtractedPage,
    detect_boilerplate_lines,
    extract_page_content,
    strip_boilerplate,
)
from src.knowledge_exporter.page_cache import PageCache
from src.knowledge_exporter.page_fetcher import PageFetcher, content_hash
from src.knowledge_exporter.page_meta import (
    detect_noindex,
    detect_page_type_from_html,
    normalize_page_type,
    url_to_slug,
)
from src.knowledge_exporter.rag_ai import looks_like_category_listing, structure_page_markdown
from src.knowledge_exporter.rag_writer import RagPageDocument, RagWriter
from src.knowledge_exporter.sitemap_lastmod import fetch_url_lastmod_map

logger = logging.getLogger(__name__)


@dataclass
class ExportSummary:
    """Final export statistics."""

    total_urls: int = 0
    success: int = 0
    failed: int = 0
    duplicate: int = 0
    empty: int = 0
    cached: int = 0
    skipped_noindex: int = 0
    skipped_unchanged: int = 0
    rag_files: int = 0
    parts: int = 0
    total_bytes: int = 0
    output_dir: str = ""
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize summary for API/job result."""
        return {
            "total_urls": self.total_urls,
            "success": self.success,
            "failed": self.failed,
            "duplicate": self.duplicate,
            "empty": self.empty,
            "cached": self.cached,
            "skipped_noindex": self.skipped_noindex,
            "skipped_unchanged": self.skipped_unchanged,
            "rag_files": self.rag_files,
            "parts": self.parts,
            "total_bytes": self.total_bytes,
            "output_dir": self.output_dir,
            "warnings": self.warnings[:50],
        }

    def print_report(self) -> None:
        """Print human-readable summary to stdout."""
        print("\n" + "=" * 60)
        print("Knowledge Export Summary")
        print("=" * 60)
        print(f"  Output directory : {self.output_dir}")
        print(f"  Total URLs       : {self.total_urls}")
        print(f"  Successful       : {self.success}")
        print(f"  Failed           : {self.failed}")
        print(f"  Duplicate content: {self.duplicate}")
        print(f"  Empty/short      : {self.empty}")
        print(f"  From cache       : {self.cached}")
        print(f"  Skipped noindex  : {self.skipped_noindex}")
        print(f"  Skipped unchanged: {self.skipped_unchanged}")
        print(f"  RAG page files   : {self.rag_files}")
        print(f"  Part files       : {self.parts}")
        print(f"  Total size       : {self.total_bytes / 1024:.1f} KB")
        if self.warnings:
            print(f"  Warnings         : {len(self.warnings)}")
            for w in self.warnings[:10]:
                print(f"    - {w}")
            if len(self.warnings) > 10:
                print(f"    ... and {len(self.warnings) - 10} more")
        print("=" * 60 + "\n")


class KnowledgeExporter:
    """
    Export sitemap pages to per-URL RAG Markdown and optional part files.
    """

    def __init__(self, config: KnowledgeExporterConfig, *, llm_model: Any = None) -> None:
        """
        Initialize exporter with configuration.

        Input:
            config: KnowledgeExporterConfig instance.
            llm_model: Optional AIModel instance for LLM structuring.
        """
        self.config = config
        self.llm_model = llm_model
        self.cache = PageCache(config.cache_dir)
        self.fetcher = PageFetcher(
            cache=self.cache,
            timeout=config.timeout,
            max_retries=config.max_retries,
        )
        self._lastmod_map: Dict[str, str] = dict(config.lastmod_map or {})

    def _load_lastmod_map(self) -> None:
        """Fetch sitemap lastmod map when not preloaded."""
        if self._lastmod_map or not self.config.sitemap_url:
            return
        self._lastmod_map = fetch_url_lastmod_map(
            self.config.sitemap_url,
            timeout=self.config.timeout,
            max_retries=self.config.max_retries,
        )

    def resolve_urls(self) -> tuple[List[str], Optional[str]]:
        """
        Resolve URL list from config or sitemap.

        Output:
            Tuple of (filtered URLs, error message).
        """
        if self.config.urls:
            raw = self._apply_product_sample_limit(list(self.config.urls))
            return [u for u in raw if self.config.url_allowed(u)], None
        elif self.config.sitemap_url:
            raw, error, _sources = fetch_all_sitemap_urls(
                self.config.sitemap_url,
                max_retries=self.config.max_retries,
                timeout=self.config.timeout,
            )
            if error:
                return [], error
            self._load_lastmod_map()
            raw = self._apply_product_sample_limit(raw)
        else:
            return [], "Provide --sitemap URL or --urls-file"

        filtered = [u for u in raw if self.config.url_allowed(u)]
        return filtered, None

    def _apply_product_sample_limit(self, urls: List[str]) -> List[str]:
        """Limit product URLs only when product_sample_limit > 0."""
        limit = self.config.product_sample_limit
        if limit <= 0:
            return urls
        type_map = self.config.url_page_types or {}
        products = [u for u in urls if normalize_page_type(type_map.get(u)) == "product"]
        others = [u for u in urls if normalize_page_type(type_map.get(u)) != "product"]
        return others + products[:limit]

    def _page_type_for(self, url: str, html: bytes) -> str:
        """Resolve page type from analysis map or HTML detection."""
        if self.config.url_page_types and url in self.config.url_page_types:
            return normalize_page_type(self.config.url_page_types[url])
        return normalize_page_type(detect_page_type_from_html(html, url))

    def _should_skip_unchanged(self, url: str, extract_hash: str) -> bool:
        """Check registry for unchanged lastmod + content hash."""
        if not self.config.skip_unchanged or not self.config.project_slug:
            return False
        try:
            from web.app.services.knowledge_export_store import get_registry_row

            row = get_registry_row(self.config.project_slug, url)
            if not row or row.get("status") != "exported":
                return False
            lastmod = (self._lastmod_map.get(url) or "").strip()
            reg_lm = (row.get("sitemap_lastmod") or "").strip()
            if lastmod and reg_lm and lastmod != reg_lm:
                return False
            return bool(row.get("content_hash")) and row.get("content_hash") == extract_hash
        except Exception:
            return False

    def _process_one(self, url: str, crawled_at: str) -> RagPageDocument:
        """
        Fetch, extract, optionally LLM-structure one page.

        Output:
            RagPageDocument with export status.
        """
        lastmod = self._lastmod_map.get(url, "")

        result = self.fetcher.fetch(url)
        if not result.html:
            return RagPageDocument(
                url=url,
                title="",
                description="",
                lang="",
                markdown_body="",
                crawled_at=crawled_at,
                status="failed",
                error=result.error or "No content",
                sitemap_lastmod=lastmod,
            )

        page_type = self._page_type_for(url, result.html)
        if page_type == "blog" and not self.config.include_blog:
            return RagPageDocument(
                url=url,
                title="",
                description="",
                lang="",
                markdown_body="",
                crawled_at=crawled_at,
                status="skipped_filter",
                page_type=page_type,
                sitemap_lastmod=lastmod,
            )

        is_noidx = detect_noindex(result.html)
        if is_noidx and not self.config.include_noindex:
            return RagPageDocument(
                url=url,
                title="",
                description="",
                lang="",
                markdown_body="",
                crawled_at=crawled_at,
                status="skipped_noindex",
                page_type=page_type,
                is_noindex=True,
                sitemap_lastmod=lastmod,
            )

        try:
            extracted: ExtractedPage = extract_page_content(result.html, url)
        except Exception as exc:
            logger.exception("Extract failed for %s", url)
            return RagPageDocument(
                url=url,
                title="",
                description="",
                lang="",
                markdown_body="",
                crawled_at=crawled_at,
                status="failed",
                error=str(exc),
                page_type=page_type,
                sitemap_lastmod=lastmod,
            )

        extract_hash = content_hash(extracted.markdown)
        if self._should_skip_unchanged(url, extract_hash):
            return RagPageDocument(
                url=url,
                title=extracted.title,
                description=extracted.description,
                lang=extracted.lang,
                markdown_body=extracted.markdown,
                crawled_at=crawled_at,
                status="skipped_unchanged",
                content_hash=extract_hash,
                page_type=page_type,
                slug=url_to_slug(url),
                sitemap_lastmod=lastmod,
                is_noindex=is_noidx,
            )

        # Category/archive listings are not single products — skip for product RAG
        if page_type == "product" and looks_like_category_listing(extracted.markdown):
            return RagPageDocument(
                url=url,
                title=extracted.title,
                description=extracted.description,
                lang=extracted.lang,
                markdown_body="",
                crawled_at=crawled_at,
                status="skipped_filter",
                content_hash=extract_hash,
                page_type="category",
                slug=url_to_slug(url),
                sitemap_lastmod=lastmod,
                is_noindex=is_noidx,
                error="category_listing_skipped",
            )

        status = "cached" if result.from_cache else "success"
        if extracted.char_count < self.config.min_content_chars:
            return RagPageDocument(
                url=url,
                title=extracted.title,
                description=extracted.description,
                lang=extracted.lang,
                markdown_body=extracted.markdown,
                crawled_at=crawled_at,
                status="empty",
                content_hash=extract_hash,
                page_type=page_type,
                slug=url_to_slug(url),
                sitemap_lastmod=lastmod,
                is_noindex=is_noidx,
            )

        body = extracted.markdown
        llm_structured = False
        if self.config.use_llm and self.llm_model is not None:
            try:
                body = structure_page_markdown(
                    url=url,
                    title=extracted.title,
                    description=extracted.description,
                    raw_markdown=extracted.markdown,
                    page_type=page_type,
                    model=self.llm_model,
                    lang=extracted.lang or "fa",
                )
                llm_structured = True
            except RuntimeError as exc:
                if str(exc) == "credit_exhausted":
                    raise
                logger.warning("LLM failed for %s: %s", url, exc)

        return RagPageDocument(
            url=url,
            title=extracted.title,
            description=extracted.description,
            lang=extracted.lang,
            markdown_body=body,
            crawled_at=crawled_at,
            status=status,
            content_hash=content_hash(body),
            page_type=page_type,
            slug=url_to_slug(url),
            sitemap_lastmod=lastmod,
            is_noindex=is_noidx,
            llm_structured=llm_structured,
        )

    def _update_registry(self, doc: RagPageDocument) -> None:
        """Persist export row to SQLite registry."""
        if not self.config.project_slug:
            return
        try:
            from web.app.services.knowledge_export_store import upsert_page

            upsert_page(
                project_slug=self.config.project_slug,
                url=doc.url,
                page_type=doc.page_type,
                slug=doc.slug,
                relative_path=doc.relative_path,
                title=doc.title,
                content_hash=doc.content_hash,
                sitemap_lastmod=doc.sitemap_lastmod,
                status=doc.status,
                error=doc.error or "",
            )
        except Exception as exc:
            logger.warning("Registry update failed for %s: %s", doc.url, exc)

    def run(
        self,
        on_progress: Optional[Callable[[int, int, str], None]] = None,
        use_tqdm: bool = True,
    ) -> ExportSummary:
        """
        Execute full RAG export pipeline.

        Input:
            on_progress: Optional callback(processed, total, message).
            use_tqdm: Show CLI progress bar when True.

        Output:
            ExportSummary with counts and written file stats.
        """
        crawled_at = datetime.now(timezone.utc).isoformat()
        urls, error = self.resolve_urls()
        summary = ExportSummary(output_dir=str(self.config.output_dir))

        if error:
            summary.warnings.append(error)
            summary.print_report()
            return summary

        summary.total_urls = len(urls)
        if not urls:
            summary.warnings.append("No URLs to process after filtering")
            summary.print_report()
            return summary

        documents: List[RagPageDocument] = []
        seen_hashes: Set[str] = set()
        processed = 0
        total = len(urls)

        if on_progress:
            on_progress(0, total, f"Exporting 0/{total} pages…")

        with ThreadPoolExecutor(max_workers=max(1, self.config.concurrency)) as pool:
            futures = {}
            for idx, url in enumerate(urls):
                if idx > 0 and self.config.rate_limit_seconds > 0:
                    time.sleep(self.config.rate_limit_seconds / max(1, self.config.concurrency))
                futures[pool.submit(self._process_one, url, crawled_at)] = url

            iterator = as_completed(futures)
            if use_tqdm:
                iterator = tqdm(iterator, total=len(urls), desc="Exporting pages", unit="page")

            for future in iterator:
                try:
                    doc = future.result()
                except RuntimeError as exc:
                    if str(exc) == "credit_exhausted":
                        summary.warnings.append("LLM credit exhausted — export stopped")
                        break
                    raise
                url = futures[future]
                processed += 1

                if doc.status == "failed":
                    summary.failed += 1
                    summary.warnings.append(f"Failed: {url} — {doc.error}")
                    documents.append(doc)
                    self._update_registry(doc)
                elif doc.status == "skipped_noindex":
                    summary.skipped_noindex += 1
                    documents.append(doc)
                    self._update_registry(doc)
                elif doc.status == "skipped_filter":
                    documents.append(doc)
                    self._update_registry(doc)
                elif doc.status == "skipped_unchanged":
                    summary.skipped_unchanged += 1
                    documents.append(doc)
                elif doc.status == "empty":
                    summary.empty += 1
                    summary.warnings.append(
                        f"Short content ({len(doc.markdown_body)} chars): {url}"
                    )
                    documents.append(doc)
                    self._update_registry(doc)
                else:
                    if doc.content_hash and doc.content_hash in seen_hashes:
                        doc.status = "duplicate"
                        summary.duplicate += 1
                    else:
                        if doc.content_hash:
                            seen_hashes.add(doc.content_hash)
                        if doc.status == "cached":
                            summary.cached += 1
                        summary.success += 1
                    documents.append(doc)

                if on_progress:
                    on_progress(processed, total, f"Exporting {processed}/{total}…")

        # Boilerplate removal across successful pages
        success_bodies = [
            d.markdown_body for d in documents if d.status in ("success", "cached")
        ]
        boilerplate = detect_boilerplate_lines(success_bodies)
        if boilerplate:
            logger.info("Removing %d boilerplate lines", len(boilerplate))
            for doc in documents:
                if doc.status in ("success", "cached"):
                    doc.markdown_body = strip_boilerplate(doc.markdown_body, boilerplate)
                    doc.content_hash = content_hash(doc.markdown_body)

        if on_progress:
            on_progress(total, total, "Writing RAG Markdown files…")

        writer = RagWriter(
            output_dir=self.config.output_dir,
            write_parts=self.config.write_parts,
            write_per_url=self.config.write_per_url,
            max_part_bytes=self.config.max_part_bytes,
            max_pages_per_part=self.config.max_pages_per_part,
        )
        write_result = writer.write_all(
            [d for d in documents if d.status not in ("skipped_unchanged",)]
        )
        summary.rag_files = len(write_result.get("written_paths") or [])
        summary.parts = len(write_result.get("parts") or [])

        for doc in documents:
            if doc.status in ("success", "cached") and doc.relative_path:
                self._update_registry(doc)
            elif doc.status in ("failed", "empty", "skipped_noindex", "skipped_filter"):
                self._update_registry(doc)

        total_bytes = 0
        for rel in write_result.get("written_paths") or []:
            path = self.config.output_dir / rel
            if path.exists():
                total_bytes += path.stat().st_size
        for name in write_result.get("parts") or []:
            path = self.config.output_dir / name
            if path.exists():
                total_bytes += path.stat().st_size
        summary.total_bytes = total_bytes

        summary.print_report()
        return summary
