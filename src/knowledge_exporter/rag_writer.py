"""
Per-URL RAG Markdown writer — {page_type}/{slug}.md layout.

Input:
    Structured page documents with metadata.

Output:
    Individual UTF-8 Markdown files under pages/ directory.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from src.knowledge_exporter.part_writer import DOCUMENT_SEPARATOR, PageDocument, PartWriter

logger = logging.getLogger(__name__)


@dataclass
class RagPageDocument(PageDocument):
    """Extended page document for per-URL RAG export."""

    page_type: str = "other"
    slug: str = ""
    relative_path: str = ""
    sitemap_lastmod: str = ""
    is_noindex: bool = False
    llm_structured: bool = False


@dataclass
class RagWriter:
    """
    Write per-URL Markdown files and optional legacy part bundles.

    Input:
        output_dir: Project knowledge_export folder.
        pages_subdir: Relative folder for per-URL files (default pages).
    """

    output_dir: Path
    pages_subdir: str = "pages"
    write_parts: bool = True
    max_part_bytes: int = 500 * 1024
    max_pages_per_part: int = 50

    written_paths: List[str] = field(default_factory=list)
    used_slugs: Set[str] = field(default_factory=set)

    def _unique_slug(self, page_type: str, slug: str) -> str:
        """Avoid slug collisions within same page_type folder."""
        base = slug or "page"
        candidate = base
        n = 2
        key = f"{page_type}/{candidate}"
        while key in self.used_slugs:
            candidate = f"{base}-{n}"
            key = f"{page_type}/{candidate}"
            n += 1
        self.used_slugs.add(key)
        return candidate

    def render_rag_document(self, doc: RagPageDocument) -> str:
        """
        Render RAG-standard Markdown with YAML frontmatter.

        Output:
            Full file content (UTF-8).
        """
        title_fm = (doc.title or "").replace('"', '\\"')
        desc_fm = (doc.description or "").replace('"', '\\"')
        lines = [
            "---",
            f"url: {doc.url}",
            f'title: "{title_fm}"',
            f"page_type: {doc.page_type}",
            f"lang: {doc.lang or 'fa'}",
            f"crawled_at: {doc.crawled_at}",
        ]
        if doc.sitemap_lastmod:
            lines.append(f"sitemap_lastmod: {doc.sitemap_lastmod}")
        if doc.content_hash:
            lines.append(f"content_hash: {doc.content_hash}")
        lines.append(f"source: knowledge_export")
        if desc_fm:
            lines.append(f'description: "{desc_fm}"')
        lines.append("---")
        lines.append("")
        body = doc.markdown_body.strip()
        if not body.startswith("#"):
            body = f"# {doc.title}\n\n{body}"
        return "\n".join(lines) + "\n" + body + "\n"

    def write_page_file(self, doc: RagPageDocument) -> Optional[str]:
        """
        Write one page to {page_type}/{slug}.md.

        Output:
            Repo-relative path string or None on skip.
        """
        if doc.status not in ("success", "cached") or not doc.markdown_body.strip():
            return None

        page_type = doc.page_type or "other"
        slug = self._unique_slug(page_type, doc.slug or "page")
        rel = f"{self.pages_subdir}/{page_type}/{slug}.md"
        path = self.output_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.render_rag_document(doc), encoding="utf-8")
        doc.slug = slug
        doc.relative_path = rel
        self.written_paths.append(rel)
        logger.info("Wrote RAG page %s", rel)
        return rel

    def write_all(
        self,
        documents: List[RagPageDocument],
    ) -> Dict[str, Any]:
        """
        Write per-URL files and optional part files + index.json.

        Output:
            Summary dict with paths and index entries.
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        index_entries: List[Dict[str, Any]] = []

        exportable: List[RagPageDocument] = []
        for doc in documents:
            rel = self.write_page_file(doc)
            entry: Dict[str, Any] = {
                "url": doc.url,
                "title": doc.title,
                "page_type": doc.page_type,
                "relative_path": doc.relative_path or rel,
                "slug": doc.slug,
                "char_count": len(doc.markdown_body),
                "status": doc.status,
                "content_hash": doc.content_hash,
                "crawled_at": doc.crawled_at,
                "sitemap_lastmod": doc.sitemap_lastmod,
                "is_noindex": doc.is_noindex,
                "llm_structured": doc.llm_structured,
            }
            if doc.error:
                entry["error"] = doc.error
            index_entries.append(entry)
            if rel:
                exportable.append(doc)

        parts: List[str] = []
        if self.write_parts and exportable:
            part_docs = [
                PageDocument(
                    url=d.url,
                    title=d.title,
                    description=d.description,
                    lang=d.lang,
                    markdown_body=d.markdown_body,
                    crawled_at=d.crawled_at,
                    status=d.status,
                    content_hash=d.content_hash,
                )
                for d in exportable
            ]
            writer = PartWriter(
                output_dir=self.output_dir,
                max_part_bytes=self.max_part_bytes,
                max_pages_per_part=self.max_pages_per_part,
            )
            parts = writer.write_all(part_docs)
            for entry in index_entries:
                for ie in writer.index_entries:
                    if ie.get("url") == entry.get("url"):
                        entry["part_file"] = ie.get("part_file")
                        break

        index_path = self.output_dir / "index.json"
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "format": "rag_per_url",
            "total_pages": len(documents),
            "exported_files": len(self.written_paths),
            "parts": parts,
            "pages": index_entries,
        }
        index_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        return {
            "parts": parts,
            "written_paths": list(self.written_paths),
            "index_path": str(index_path),
        }
