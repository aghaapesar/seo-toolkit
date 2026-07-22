"""
Markdown part writer and index.json generator.

Input:
    List of rendered Markdown documents.

Output:
    knowledge_part_XX.md files and index.json manifest.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

logger = logging.getLogger(__name__)

# Join complete documents with blank lines only.
# Do NOT insert a lone `---` — that would look like empty frontmatter and
# break RAG section splitting (standard §2 splits on metadata blocks).
DOCUMENT_SEPARATOR = "\n\n"
PartStatus = Literal["success", "failed", "duplicate", "empty", "cached"]


@dataclass
class PageDocument:
    """One page ready for export."""

    url: str
    title: str
    description: str
    lang: str
    markdown_body: str
    crawled_at: str
    status: PartStatus
    error: Optional[str] = None
    content_hash: Optional[str] = None

    def render(self) -> str:
        """
        Render full Markdown document with RAG-standard frontmatter.

        Per docs/RAG_CONTENT_STANDARD.md: only `url` + `title` in metadata.
        """
        title = (self.title or "").strip() or "بدون عنوان"
        title_fm = title.replace('"', '\\"')
        frontmatter = (
            "---\n"
            f"url: {self.url}\n"
            f'title: "{title_fm}"\n'
            "---\n\n"
        )
        body = (self.markdown_body or "").strip()
        if not body.startswith("#"):
            body = f"# {title}\n\n{body}"
        return frontmatter + body


@dataclass
class PartWriter:
    """
    Split documents into size/page-limited part files.

    Critical: never splits a single document / product across parts.
    If one product exceeds max_part_bytes alone, it still occupies its own
    complete part file so RAG never sees a truncated product mid-document.
    """

    output_dir: Path
    max_part_bytes: int = 500 * 1024
    max_pages_per_part: int = 50

    parts_written: List[str] = field(default_factory=list)
    index_entries: List[Dict[str, Any]] = field(default_factory=list)

    def _part_filename(self, part_num: int) -> str:
        """Return zero-padded part filename."""
        return f"knowledge_part_{part_num:02d}.md"

    def write_all(self, documents: List[PageDocument]) -> List[str]:
        """
        Write all successful documents into part files.

        Input:
            documents: Page documents (failed/duplicate may be indexed only).

        Output:
            List of written part filenames.
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        exportable = [d for d in documents if d.status in ("success", "cached") and d.markdown_body.strip()]

        part_num = 1
        current_docs: List[str] = []
        current_bytes = 0
        current_count = 0

        def flush_part() -> None:
            nonlocal part_num, current_docs, current_bytes, current_count
            if not current_docs:
                return
            filename = self._part_filename(part_num)
            path = self.output_dir / filename
            content = DOCUMENT_SEPARATOR.join(current_docs)
            path.write_text(content, encoding="utf-8")
            self.parts_written.append(filename)
            logger.info("Wrote %s (%d docs, %d bytes)", filename, current_count, len(content.encode("utf-8")))
            part_num += 1
            current_docs = []
            current_bytes = 0
            current_count = 0

        part_map: Dict[str, str] = {}

        for doc in exportable:
            rendered = doc.render()
            doc_bytes = len(rendered.encode("utf-8"))
            separator_bytes = len(DOCUMENT_SEPARATOR.encode("utf-8")) if current_docs else 0

            would_exceed_size = current_docs and (current_bytes + separator_bytes + doc_bytes > self.max_part_bytes)
            would_exceed_count = current_docs and current_count >= self.max_pages_per_part

            if would_exceed_size or would_exceed_count:
                flush_part()

            if not current_docs:
                current_bytes = 0
            else:
                current_bytes += separator_bytes
            current_docs.append(rendered)
            current_bytes += doc_bytes
            current_count += 1
            part_map[doc.url] = self._part_filename(part_num)

        flush_part()

        self._build_index(documents, part_map)
        return self.parts_written

    def _build_index(self, documents: List[PageDocument], part_map: Dict[str, str]) -> None:
        """Write index.json manifest."""
        for doc in documents:
            entry: Dict[str, Any] = {
                "url": doc.url,
                "title": doc.title,
                "part_file": part_map.get(doc.url),
                "char_count": len(doc.markdown_body),
                "status": doc.status,
                "content_hash": doc.content_hash,
                "crawled_at": doc.crawled_at,
            }
            if doc.error:
                entry["error"] = doc.error
            self.index_entries.append(entry)

        index_path = self.output_dir / "index.json"
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_pages": len(documents),
            "parts": self.parts_written,
            "pages": self.index_entries,
        }
        index_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("Wrote index.json (%d pages)", len(documents))
