"""Safe file download helpers for web exports."""

from pathlib import Path
from typing import Dict, List, Optional

ALLOWED_DOWNLOAD_ROOTS = (
    Path("output"),
    Path("projects"),
    Path("index_history"),
)

DEFAULT_LABELS = {
    "new_urls": "new_urls.txt",
    "already_submitted": "already_submitted.txt",
    "url_status_json": "url_status.json",
    "url_status_csv": "url_status.csv",
    "url_status_latest_json": "url_status_latest.json",
    "url_status_latest_csv": "url_status_latest.csv",
    "sitemap_latest": "sitemap_latest.txt",
    "sitemap_archive": "sitemap_archive.txt",
}


def project_root() -> Path:
    """Return repository root (cwd when uvicorn runs)."""
    return Path.cwd().resolve()


def _relative_to_root(path: Path) -> str:
    """Return repo-relative path string for a file."""
    root = project_root()
    resolved = path.resolve()
    return str(resolved.relative_to(root))


def resolve_download_path(relative_path: str) -> Path:
    """
    Resolve and validate a user-facing file path for download.

    Input:
        relative_path: Repo-relative path from export registry.

    Output:
        Absolute resolved file path.

    Raises:
        ValueError: Path escapes allowed roots or is not a file.
    """
    root = project_root()
    candidate = (root / relative_path).resolve()

    allowed = False
    for base in ALLOWED_DOWNLOAD_ROOTS:
        base_resolved = (root / base).resolve()
        try:
            candidate.relative_to(base_resolved)
            allowed = True
            break
        except ValueError:
            continue

    if not allowed:
        raise ValueError("File path is not in an allowed download directory")
    if not candidate.is_file():
        raise ValueError("File not found")
    return candidate


def file_entry(kind: str, label: str, path: str) -> dict:
    """
    Build a downloadable file descriptor for API/UI.

    Input:
        kind: Machine id (new_urls, url_status_csv, …).
        label: Human label.
        path: Path on disk (absolute or repo-relative).

    Output:
        Dict with name, kind, path, download_url.
    """
    file_path = Path(path)
    if not file_path.is_absolute():
        file_path = project_root() / file_path
    rel = _relative_to_root(file_path)
    return {
        "kind": kind,
        "label": label,
        "name": file_path.name,
        "path": rel,
        "download_url": f"/api/v1/index-diff/download?path={rel}",
    }


def flatten_run_files(run: dict, labels: Optional[Dict[str, str]] = None) -> List[dict]:
    """
    Convert export run file map to downloadable entries.

    Input:
        run: One export_runs record from UrlIndexTracker.
        labels: Optional kind -> label map.

    Output:
        List of file_entry dicts (skips missing files).
    """
    kind_labels = labels or {}
    entries: List[dict] = []
    for kind, path in (run.get("files") or {}).items():
        if not path:
            continue
        try:
            rel = path if not Path(path).is_absolute() else _relative_to_root(Path(path))
            resolve_download_path(rel)
        except ValueError:
            continue
        label = kind_labels.get(kind) or DEFAULT_LABELS.get(kind) or kind
        entries.append(file_entry(kind, label, path))
    return entries
