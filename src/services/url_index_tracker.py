"""
URL Index Tracker - track submitted URLs and diff against new sitemaps.

Persists per-domain history so indexing tools only receive new URLs.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import unquote, urlparse


def normalize_url(url: str) -> str:
    """
    Normalize URL for stable comparison.

    Input:
        url: Raw URL string.

    Output:
        Normalized URL (lowercase host, decoded path, no trailing slash).
    """
    parsed = urlparse(url.strip())
    if not parsed.scheme or not parsed.netloc:
        return url.strip()

    path = unquote(parsed.path.rstrip("/") or "")
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{path}{query}"


class UrlIndexTracker:
    """
    Track URLs submitted to indexing tools and diff new sitemap fetches.

    Storage layout:
        index_history/{domain}/history.json
    """

    def __init__(self, domain: str, base_dir: str = "index_history", flat: bool = False) -> None:
        """
        Initialize tracker for a domain.

        Input:
            domain: Site domain or project identifier.
            base_dir: Root directory for persisted history.
            flat: When True, use base_dir directly (per-project folder).
        """
        self.domain = domain
        self.base_dir = Path(base_dir)
        if flat:
            self.project_dir = self.base_dir
        else:
            self.project_dir = self.base_dir / self._sanitize_name(domain)
        self.project_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.project_dir / "history.json"
        self._data = self._load_history()

    @staticmethod
    def _sanitize_name(name: str) -> str:
        """Convert domain/project name to a safe directory name."""
        return re.sub(r"[^\w\-.]", "_", name).lower()

    def _default_history(self) -> Dict:
        """Default empty history payload."""
        return {
            "domain": self.domain,
            "submitted_urls": [],
            "batches": [],
            "last_sitemap_fetch": None,
        }

    def _load_history(self) -> Dict:
        """Load JSON history or return defaults."""
        if not self.history_file.exists():
            return self._default_history()

        with open(self.history_file, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        data.setdefault("submitted_urls", [])
        data.setdefault("batches", [])
        return data

    def _save_history(self) -> None:
        """Persist history JSON to disk."""
        with open(self.history_file, "w", encoding="utf-8") as handle:
            json.dump(self._data, handle, ensure_ascii=False, indent=2)

    def load_submitted_urls(self) -> Set[str]:
        """
        Return normalized set of previously submitted URLs.

        Output:
            Set of normalized URL strings.
        """
        return {normalize_url(url) for url in self._data.get("submitted_urls", [])}

    def diff(self, current_urls: List[str]) -> Tuple[List[str], List[str]]:
        """
        Split current sitemap URLs into new vs already submitted.

        Input:
            current_urls: URLs from latest sitemap fetch.

        Output:
            Tuple of (new_urls, already_submitted_urls), both sorted.
        """
        submitted = self.load_submitted_urls()
        seen: Set[str] = set()
        new_urls: List[str] = []
        already: List[str] = []

        for raw in current_urls:
            normalized = normalize_url(raw)
            if normalized in seen:
                continue
            seen.add(normalized)

            if normalized in submitted:
                already.append(raw.strip())
            else:
                new_urls.append(raw.strip())

        self._data["last_sitemap_fetch"] = datetime.now().isoformat()
        self._save_history()
        return sorted(new_urls), sorted(already)

    def import_from_txt(self, file_path: str) -> int:
        """
        Import previously submitted URLs from a text file.

        Input:
            file_path: Path to newline-delimited URL file.

        Output:
            Count of newly added URLs.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Import file not found: {file_path}")

        existing = self.load_submitted_urls()
        added = 0

        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                url = line.strip()
                if not url or url.startswith("#"):
                    continue
                normalized = normalize_url(url)
                if normalized not in existing:
                    self._data["submitted_urls"].append(url)
                    existing.add(normalized)
                    added += 1

        if added:
            self._save_history()
        return added

    def import_from_txt_files(self, file_paths: List[str]) -> Dict:
        """
        Import URLs from multiple text files in one batch.

        Input:
            file_paths: List of paths to newline-delimited URL files.

        Output:
            Dict with total_added, files_processed, and per-file breakdown.
        """
        total_added = 0
        file_results: List[Dict] = []

        for file_path in file_paths:
            path = Path(file_path)
            try:
                added = self.import_from_txt(file_path)
                total_added += added
                file_results.append(
                    {"name": path.name, "added": added, "error": None}
                )
            except FileNotFoundError as exc:
                file_results.append(
                    {"name": path.name, "added": 0, "error": str(exc)}
                )

        return {
            "total_added": total_added,
            "files_processed": len(file_results),
            "files": file_results,
        }

    def mark_batch_submitted(
        self, urls: List[str], source_file: str = ""
    ) -> str:
        """
        Record a batch of URLs as submitted to an indexing tool.

        Input:
            urls: URLs that were submitted.
            source_file: Optional export filename for audit trail.

        Output:
            Batch identifier string.
        """
        batch_id = hashlib.md5(
            f"{datetime.now().isoformat()}-{uuid.uuid4()}".encode()
        ).hexdigest()[:12]

        existing = self.load_submitted_urls()
        added_urls: List[str] = []

        for raw in urls:
            normalized = normalize_url(raw)
            if normalized not in existing:
                self._data["submitted_urls"].append(raw.strip())
                existing.add(normalized)
                added_urls.append(raw.strip())

        self._data["batches"].append(
            {
                "id": batch_id,
                "submitted_at": datetime.now().isoformat(),
                "url_count": len(added_urls),
                "source_file": source_file,
            }
        )
        self._save_history()
        return batch_id

    def export_txt(self, urls: List[str], output_path: Path) -> Path:
        """
        Export URL list to a plain text file.

        Input:
            urls: URLs to write.
            output_path: Destination file path.

        Output:
            Path to written file.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as handle:
            for url in urls:
                handle.write(f"{url}\n")
        return output_path

    def get_status(self) -> Dict:
        """
        Return tracker statistics for the domain.

        Output:
            Dictionary with counts and last batch metadata.
        """
        batches = self._data.get("batches", [])
        last_batch = batches[-1] if batches else None
        return {
            "domain": self.domain,
            "total_submitted": len(self._data.get("submitted_urls", [])),
            "batch_count": len(batches),
            "last_batch": last_batch,
            "last_sitemap_fetch": self._data.get("last_sitemap_fetch"),
        }
