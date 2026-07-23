"""
Per-topic RAG Markdown writer — multi-product part files (primary).

Input:
    Structured page documents with metadata.

Output:
    knowledge_part_XX.md bundles (many products per file; never mid-splits
    one product) + index.json. Optional per-URL files under pages/ when enabled.

Format per docs/RAG_CONTENT_STANDARD.md §2 (url + title frontmatter per topic).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from src.knowledge_exporter.part_writer import PageDocument, PartWriter

logger = logging.getLogger(__name__)


@dataclass
class RagPageDocument(PageDocument):
    """Extended page document for RAG export."""

    page_type: str = "other"
    slug: str = ""
    relative_path: str = ""
    sitemap_lastmod: str = ""
    is_noindex: bool = False
    llm_structured: bool = False


@dataclass
class RagWriter:
    """
    Write multi-product part files (default) and optional per-URL copies.

    Input:
        output_dir: Project knowledge_export folder.
        write_parts: Write knowledge_part_*.md (default True — primary output).
        write_per_url: Also write pages/{type}/{slug}.md (default False).
    """

    output_dir: Path
    pages_subdir: str = "pages"
    write_parts: bool = True
    write_per_url: bool = False
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
        Render one topic with RAG-standard frontmatter (url + title only).
        """
        title = (doc.title or "").strip() or "بدون عنوان"
        title_fm = title.replace('"', '\\"')
        lines = [
            "---",
            f"url: {doc.url}",
            f'title: "{title_fm}"',
            "---",
            "",
        ]
        body = (doc.markdown_body or "").strip()
        if body.startswith("---"):
            parts = body.split("---", 2)
            if len(parts) >= 3:
                body = parts[2].strip()
        if not body.startswith("#"):
            body = f"# {title}\n\n{body}"
        return "\n".join(lines) + "\n" + body + "\n"

    def write_page_file(self, doc: RagPageDocument) -> Optional[str]:
        """
        Write one optional per-URL file under pages/.

        Output:
            Repo-relative path or None when skipped / write_per_url off.
        """
        if not self.write_per_url:
            return None
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
        logger.info("Wrote per-URL RAG page %s", rel)
        return rel

    def write_all(
        self,
        documents: List[RagPageDocument],
    ) -> Dict[str, Any]:
        """
        Write part bundles (primary) and optional per-URL files + index.json.

        Output:
            Summary with parts, written_paths, index_path.
            Each product is wholly inside one part file (never split).
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        index_entries: List[Dict[str, Any]] = []

        exportable: List[RagPageDocument] = []
        for doc in documents:
            if doc.status in ("success", "cached") and (doc.markdown_body or "").strip():
                if not doc.slug:
                    doc.slug = self._unique_slug(doc.page_type or "other", doc.slug or "page")
                exportable.append(doc)
                # Optional per-URL copy
                self.write_page_file(doc)

            entry: Dict[str, Any] = {
                "url": doc.url,
                "title": doc.title,
                "page_type": doc.page_type,
                "relative_path": doc.relative_path,
                "slug": doc.slug,
                "char_count": len(doc.markdown_body or ""),
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
            # Map each URL → part file; registry relative_path prefers the part
            url_to_part = {
                ie.get("url"): ie.get("part_file")
                for ie in writer.index_entries
                if ie.get("part_file")
            }
            for doc in exportable:
                part_name = url_to_part.get(doc.url)
                if part_name:
                    doc.relative_path = part_name
            for entry in index_entries:
                part_name = url_to_part.get(entry.get("url"))
                if part_name:
                    entry["part_file"] = part_name
                    entry["relative_path"] = part_name
            self.written_paths.extend(parts)
        elif exportable and not self.write_parts and self.write_per_url:
            # Per-URL only mode: relative_path already set in write_page_file
            for doc in exportable:
                if doc.relative_path:
                    for entry in index_entries:
                        if entry.get("url") == doc.url:
                            entry["relative_path"] = doc.relative_path

        index_path = self.output_dir / "index.json"
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "format": "rag_multipart" if parts else "rag_per_url",
            "total_pages": len(documents),
            "exported_topics": len(exportable),
            "exported_files": len(parts) if parts else len(self.written_paths),
            "parts": parts,
            "write_per_url": self.write_per_url,
            "pages": index_entries,
        }
        index_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        return {
            "parts": parts,
            "written_paths": list(self.written_paths),
            "index_path": str(index_path),
        }
