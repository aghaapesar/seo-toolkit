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
        index_history/{domain}/sitemap_latest.txt
        index_history/{domain}/snapshots/sitemap_YYYYMMDD_HHMMSS.txt
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
        self.snapshots_dir = self.project_dir / "snapshots"
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.project_dir / "history.json"
        self.sitemap_latest_file = self.project_dir / "sitemap_latest.txt"
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
            "sitemap_snapshot": None,
            "last_pending_batch": None,
            "diff_exclusions": [],
            "export_runs": [],
        }

    def _load_history(self) -> Dict:
        """Load JSON history or return defaults."""
        if not self.history_file.exists():
            return self._default_history()

        with open(self.history_file, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        data.setdefault("submitted_urls", [])
        data.setdefault("batches", [])
        data.setdefault("sitemap_snapshot", None)
        data.setdefault("last_pending_batch", None)
        data.setdefault("diff_exclusions", [])
        data.setdefault("export_runs", [])
        return data

    def _save_history(self) -> None:
        """Persist history JSON to disk."""
        with open(self.history_file, "w", encoding="utf-8") as handle:
            json.dump(self._data, handle, ensure_ascii=False, indent=2)

    @staticmethod
    def _read_urls_from_file(file_path: str) -> List[str]:
        """
        Parse newline-delimited URLs from a text file.

        Input:
            file_path: Path to txt file.

        Output:
            List of raw URL strings.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Import file not found: {file_path}")

        urls: List[str] = []
        seen: Set[str] = set()
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                url = line.strip()
                if not url or url.startswith("#"):
                    continue
                normalized = normalize_url(url)
                if normalized not in seen:
                    seen.add(normalized)
                    urls.append(url)
        return urls

    def load_submitted_urls(self) -> Set[str]:
        """
        Return normalized set of previously submitted URLs.

        Output:
            Set of normalized URL strings.
        """
        return {normalize_url(url) for url in self._data.get("submitted_urls", [])}

    def load_excluded_urls(self) -> Set[str]:
        """
        Return URLs excluded from diff (submitted + temporary import exclusions).

        Output:
            Normalized URL set used when splitting new vs already.
        """
        excluded = self.load_submitted_urls()
        for raw in self._data.get("diff_exclusions", []):
            excluded.add(normalize_url(raw))
        return excluded

    def add_diff_exclusions(self, urls: List[str]) -> int:
        """
        Temporarily exclude URLs from diff without marking as submitted.

        Input:
            urls: URLs from import preview (mark_submitted=False).

        Output:
            Count of newly added exclusion entries.
        """
        existing = self.load_excluded_urls()
        stored = {normalize_url(u) for u in self._data.get("diff_exclusions", [])}
        added = 0
        for raw in urls:
            normalized = normalize_url(raw)
            if normalized not in existing:
                self._data.setdefault("diff_exclusions", []).append(raw.strip())
                stored.add(normalized)
                existing.add(normalized)
                added += 1
        if added:
            self._save_history()
        return added

    def save_sitemap_snapshot(self, urls: List[str]) -> Dict:
        """
        Persist latest sitemap URL list and archive a timestamped copy.

        Input:
            urls: Full sitemap URL list from the latest fetch.

        Output:
            Snapshot metadata dict stored in history.
        """
        unique_urls = self._dedupe_urls(urls)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = self.snapshots_dir / f"sitemap_{stamp}.txt"
        self.export_txt(unique_urls, archive_path)
        self.export_txt(unique_urls, self.sitemap_latest_file)

        meta = {
            "fetched_at": datetime.now().isoformat(),
            "url_count": len(unique_urls),
            "latest_file": str(self.sitemap_latest_file),
            "archive_file": str(archive_path),
        }
        self._data["sitemap_snapshot"] = meta
        self._data["last_sitemap_fetch"] = meta["fetched_at"]
        self._save_history()
        return meta

    @staticmethod
    def _dedupe_urls(urls: List[str]) -> List[str]:
        """Return unique URLs preserving first-seen order."""
        seen: Set[str] = set()
        unique: List[str] = []
        for raw in urls:
            normalized = normalize_url(raw)
            if normalized in seen:
                continue
            seen.add(normalized)
            unique.append(raw.strip())
        return unique

    def diff(self, current_urls: List[str]) -> Tuple[List[str], List[str]]:
        """
        Split current sitemap URLs into new vs already submitted.

        Input:
            current_urls: URLs from latest sitemap fetch.

        Output:
            Tuple of (new_urls, already_submitted_urls), both sorted.
        """
        self.save_sitemap_snapshot(current_urls)

        submitted = self.load_excluded_urls()
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

        return sorted(new_urls), sorted(already)

    def set_last_pending_batch(self, urls: List[str], source_file: str) -> None:
        """
        Remember the latest diff export awaiting index-tool submission.

        Input:
            urls: New URLs from the latest diff.
            source_file: Path or filename of exported txt.
        """
        self._data["last_pending_batch"] = {
            "created_at": datetime.now().isoformat(),
            "url_count": len(urls),
            "source_file": source_file,
            "urls": list(urls),
        }
        self._save_history()

    def mark_last_pending_batch(self) -> str:
        """
        Mark the most recent pending diff batch as submitted.

        Output:
            Batch identifier.

        Raises:
            ValueError: When no pending batch exists.
        """
        pending = self._data.get("last_pending_batch")
        if not pending or not pending.get("urls"):
            raise ValueError("No pending batch to mark. Run a diff first.")

        batch_id = self.mark_batch_submitted(
            pending["urls"],
            source_file=pending.get("source_file", ""),
        )
        self._data["last_pending_batch"] = None
        self._save_history()
        return batch_id

    def import_from_txt(self, file_path: str, *, mark_submitted: bool = True) -> Dict:
        """
        Import URLs from a text file.

        Input:
            file_path: Path to newline-delimited URL file.
            mark_submitted: When True, persist URLs as submitted.

        Output:
            Dict with urls_in_file, added, parsed, skipped counts.
        """
        urls = self._read_urls_from_file(file_path)
        urls_in_file = len(urls)
        if not mark_submitted:
            parsed = self.add_diff_exclusions(urls)
            return {
                "urls_in_file": urls_in_file,
                "added": 0,
                "parsed": parsed,
                "skipped": max(0, urls_in_file - parsed),
            }

        existing = self.load_submitted_urls()
        added = 0
        for url in urls:
            normalized = normalize_url(url)
            if normalized not in existing:
                self._data["submitted_urls"].append(url)
                existing.add(normalized)
                added += 1

        if added:
            self._save_history()
        return {
            "urls_in_file": urls_in_file,
            "added": added,
            "parsed": urls_in_file,
            "skipped": max(0, urls_in_file - added),
        }

    def import_from_txt_files(
        self,
        file_paths: List[str],
        *,
        mark_submitted: bool = True,
    ) -> Dict:
        """
        Import URLs from multiple text files in one batch.

        Input:
            file_paths: List of paths to newline-delimited URL files.
            mark_submitted: When True, persist URLs as submitted.

        Output:
            Dict with total_added, files_processed, and per-file breakdown.
        """
        total_added = 0
        total_parsed = 0
        total_in_file = 0
        file_results: List[Dict] = []

        for file_path in file_paths:
            path = Path(file_path)
            try:
                result = self.import_from_txt(
                    file_path,
                    mark_submitted=mark_submitted,
                )
                total_added += result["added"]
                total_parsed += result["parsed"] if not mark_submitted else result["added"]
                total_in_file += result["urls_in_file"]
                file_results.append(
                    {
                        "name": path.name,
                        "urls_in_file": result["urls_in_file"],
                        "added": result["added"],
                        "parsed": result["parsed"],
                        "skipped": result["skipped"],
                        "error": None,
                    }
                )
            except FileNotFoundError as exc:
                file_results.append(
                    {
                        "name": path.name,
                        "urls_in_file": 0,
                        "added": 0,
                        "parsed": 0,
                        "skipped": 0,
                        "error": str(exc),
                    }
                )

        return {
            "total_added": total_added,
            "total_parsed": total_parsed if not mark_submitted else total_in_file,
            "total_in_file": total_in_file,
            "files_processed": len(file_results),
            "files": file_results,
            "mark_submitted": mark_submitted,
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

        exclusions = self._data.get("diff_exclusions", [])
        if added_urls:
            added_norm = {normalize_url(u) for u in added_urls}
            self._data["diff_exclusions"] = [
                u for u in exclusions if normalize_url(u) not in added_norm
            ]

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

    def archive_url_status(
        self,
        sitemap_urls: List[str],
        new_urls: List[str],
        already_urls: List[str],
        output_dir: Path,
        run_id: str,
    ) -> Dict:
        """
        Archive per-URL status and register export files for download.

        Input:
            sitemap_urls: Full sitemap URL list from latest fetch.
            new_urls: URLs needing index submission.
            already_urls: URLs already indexed or excluded.
            output_dir: Directory for diff txt exports.
            run_id: Timestamp stamp for this run.

        Output:
            Metadata dict with file paths and download kinds.
        """
        submitted_norm = self.load_submitted_urls()
        exclusion_raw = {normalize_url(u) for u in self._data.get("diff_exclusions", [])}
        pending_raw = {
            normalize_url(u)
            for u in (self._data.get("last_pending_batch") or {}).get("urls", [])
        }
        new_norm = {normalize_url(u) for u in new_urls}

        status_dir = self.project_dir / "url_status"
        status_dir.mkdir(parents=True, exist_ok=True)
        archive_json = status_dir / f"url_status_{run_id}.json"
        archive_csv = status_dir / f"url_status_{run_id}.csv"
        latest_json = self.project_dir / "url_status_latest.json"
        latest_csv = self.project_dir / "url_status_latest.csv"

        rows: List[Dict] = []
        for raw in self._dedupe_urls(sitemap_urls):
            normalized = normalize_url(raw)
            if normalized in pending_raw or normalized in new_norm:
                status = "pending_index"
            elif normalized in exclusion_raw and normalized not in submitted_norm:
                status = "excluded"
            elif normalized in submitted_norm:
                status = "indexed"
            else:
                status = "unknown"

            rows.append(
                {
                    "url": raw.strip(),
                    "status": status,
                    "run_id": run_id,
                    "updated_at": datetime.now().isoformat(),
                }
            )

        payload = {
            "run_id": run_id,
            "domain": self.domain,
            "created_at": datetime.now().isoformat(),
            "counts": {
                "total": len(rows),
                "pending_index": sum(1 for r in rows if r["status"] == "pending_index"),
                "indexed": sum(1 for r in rows if r["status"] == "indexed"),
                "excluded": sum(1 for r in rows if r["status"] == "excluded"),
            },
            "urls": rows,
        }

        for target in (archive_json, latest_json):
            with open(target, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)

        for target in (archive_csv, latest_csv):
            with open(target, "w", encoding="utf-8") as handle:
                handle.write("url,status,run_id,updated_at\n")
                for row in rows:
                    url_escaped = row["url"].replace(",", "%2C")
                    handle.write(
                        f"{url_escaped},{row['status']},{row['run_id']},{row['updated_at']}\n"
                    )

        snapshot = self._data.get("sitemap_snapshot") or {}
        run_record = {
            "run_id": run_id,
            "created_at": payload["created_at"],
            "counts": {
                "total": len(sitemap_urls),
                "new": len(new_urls),
                "already": len(already_urls),
                **payload["counts"],
            },
            "files": {
                "new_urls": str(output_dir / f"new_urls_{run_id}.txt"),
                "already_submitted": str(output_dir / f"already_submitted_{run_id}.txt"),
                "url_status_json": str(archive_json),
                "url_status_csv": str(archive_csv),
                "url_status_latest_json": str(latest_json),
                "url_status_latest_csv": str(latest_csv),
                "sitemap_latest": snapshot.get("latest_file"),
                "sitemap_archive": snapshot.get("archive_file"),
            },
        }

        runs: List[Dict] = self._data.setdefault("export_runs", [])
        runs.append(run_record)
        self._data["export_runs"] = runs[-50:]
        self._save_history()
        return run_record

    def list_export_runs(self) -> List[Dict]:
        """Return registered export runs newest first."""
        runs = list(self._data.get("export_runs", []))
        runs.reverse()
        return runs

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
        snapshot = self._data.get("sitemap_snapshot") or {}
        pending = self._data.get("last_pending_batch")
        return {
            "domain": self.domain,
            "total_submitted": len(self._data.get("submitted_urls", [])),
            "diff_exclusions_count": len(self._data.get("diff_exclusions", [])),
            "batch_count": len(batches),
            "last_batch": last_batch,
            "last_sitemap_fetch": self._data.get("last_sitemap_fetch"),
            "sitemap_url_count": snapshot.get("url_count", 0),
            "sitemap_latest_file": snapshot.get("latest_file"),
            "sitemap_archive_file": snapshot.get("archive_file"),
            "has_pending_batch": bool(pending and pending.get("urls")),
            "pending_batch_count": (pending or {}).get("url_count", 0),
            "pending_batch_file": (pending or {}).get("source_file"),
        }
