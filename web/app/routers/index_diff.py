"""Index diff API router."""

import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from src.services.url_index_tracker import UrlIndexTracker
from web.app.routers.projects import resolve_project_paths
from web.app.services.sitemap_fetch import (
    fetch_all_sitemap_urls,
    normalize_sitemap_url,
    parse_uploaded_sitemap_file,
)

router = APIRouter(prefix="/api/v1/index-diff", tags=["index-diff"])

UPLOAD_DIR = Path("output/web_uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _save_upload(upload: UploadFile, prefix: str) -> Path:
    """Persist uploaded file and return path."""
    suffix = Path(upload.filename or "file").suffix or ".bin"
    dest = UPLOAD_DIR / f"{prefix}_{uuid.uuid4().hex[:8]}{suffix}"
    with open(dest, "wb") as out:
        shutil.copyfileobj(upload.file, out)
    return dest


def _resolve_tracker(domain: str, project_slug: Optional[str] = None):
    """
    Build UrlIndexTracker for domain or project scope.

    Output:
        Tuple of (tracker, domain_label, output_dir).
    """
    tracker = UrlIndexTracker(domain)
    output_dir = Path("output") / "index_diff" / tracker._sanitize_name(domain)

    if project_slug:
        project, paths = resolve_project_paths(project_slug)
        tracker = UrlIndexTracker(
            project.domain,
            base_dir=str(paths.index_history_dir),
            flat=True,
        )
        domain = project.domain
        output_dir = paths.output_dir / "index_diff"

    return tracker, domain, output_dir


class DiffRequest(BaseModel):
    """Request body for sitemap diff."""

    domain: str = Field(..., min_length=3)
    sitemap_url: str
    mark_submitted: bool = False
    project_slug: Optional[str] = None


class DiffResponse(BaseModel):
    """Diff result summary."""

    domain: str
    total: int
    new_count: int
    already_count: int
    new_file: str
    already_file: str
    batch_id: Optional[str] = None
    sitemap_snapshot: Optional[dict] = None
    pending_batch_count: int = 0


def _execute_diff(
    domain: str,
    urls: List[str],
    mark_submitted: bool,
    project_slug: Optional[str] = None,
) -> DiffResponse:
    """
    Run index diff and export txt files.

    Input:
        domain: Site domain label.
        urls: Sitemap page URLs.
        mark_submitted: Whether to mark new URLs as submitted immediately.
        project_slug: Optional isolated project folder.

    Output:
        DiffResponse with counts and file paths.
    """
    tracker, domain, output_dir = _resolve_tracker(domain, project_slug)

    new_urls, already_urls = tracker.diff(urls)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_file = tracker.export_txt(new_urls, output_dir / f"new_urls_{stamp}.txt")
    already_file = tracker.export_txt(
        already_urls, output_dir / f"already_submitted_{stamp}.txt"
    )

    batch_id = None
    if mark_submitted and new_urls:
        batch_id = tracker.mark_batch_submitted(new_urls, source_file=new_file.name)
    elif new_urls:
        tracker.set_last_pending_batch(new_urls, source_file=str(new_file))

    status = tracker.get_status()
    return DiffResponse(
        domain=domain,
        total=len(urls),
        new_count=len(new_urls),
        already_count=len(already_urls),
        new_file=str(new_file),
        already_file=str(already_file),
        batch_id=batch_id,
        sitemap_snapshot=status.get("sitemap_snapshot") or tracker._data.get("sitemap_snapshot"),
        pending_batch_count=status.get("pending_batch_count", 0),
    )


@router.get("/status/{domain}")
def get_status(domain: str, project_slug: str = ""):
    """Return submitted URL statistics and sitemap snapshot info."""
    tracker, domain, _ = _resolve_tracker(domain, project_slug or None)
    return tracker.get_status()


@router.post("/import")
async def import_urls(
    domain: str = Form(...),
    urls_files: List[UploadFile] = File(...),
    project_slug: str = Form(""),
    mark_submitted: bool = Form(True),
):
    """
    Import URLs from one or more txt files.

    Input:
        mark_submitted: When True, persist as indexed; when False, parse-only preview.
    """
    if not urls_files:
        raise HTTPException(status_code=400, detail="At least one .txt file is required")

    saved_paths: List[str] = []
    for upload in urls_files:
        if not upload.filename:
            continue
        saved_paths.append(str(_save_upload(upload, "import")))

    if not saved_paths:
        raise HTTPException(status_code=400, detail="No valid files received")

    tracker, domain, _ = _resolve_tracker(domain, project_slug or None)
    result = tracker.import_from_txt_files(saved_paths, mark_submitted=mark_submitted)
    return {
        "domain": domain,
        "added": result["total_added"],
        "parsed": result["total_parsed"],
        "mark_submitted": mark_submitted,
        "files_processed": result["files_processed"],
        "files": result["files"],
        "status": tracker.get_status(),
    }


@router.post("/mark-batch")
async def mark_batch(
    domain: str = Form(...),
    project_slug: str = Form(""),
    use_pending: bool = Form(True),
    batch_file: UploadFile = File(None),
):
    """
    Mark URLs as submitted after indexing tool run.

    Input:
        use_pending: Mark the latest diff export without re-upload.
        batch_file: Optional txt file to mark instead of pending batch.
    """
    tracker, domain, _ = _resolve_tracker(domain, project_slug or None)

    if batch_file and batch_file.filename:
        raw = await batch_file.read()
        if not raw:
            raise HTTPException(status_code=400, detail="Batch file is empty")
        urls = _parse_urls_txt(raw)
        if not urls:
            raise HTTPException(status_code=400, detail="No URLs found in batch file")
        batch_id = tracker.mark_batch_submitted(urls, source_file=batch_file.filename)
        pending = tracker._data.get("last_pending_batch")
        if pending and pending.get("source_file") == batch_file.filename:
            tracker._data["last_pending_batch"] = None
            tracker._save_history()
    elif use_pending:
        try:
            batch_id = tracker.mark_last_pending_batch()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    else:
        raise HTTPException(
            status_code=400,
            detail="Upload a batch txt file or mark the pending batch",
        )

    return {
        "domain": domain,
        "batch_id": batch_id,
        "status": tracker.get_status(),
    }


@router.post("/diff", response_model=DiffResponse)
def run_diff(payload: DiffRequest):
    """
    Fetch sitemap, diff against history, export txt files.

    Input: domain + sitemap URL.
    Output: counts and output file paths.
    """
    sitemap_url = normalize_sitemap_url(payload.sitemap_url)
    urls, fetch_error = fetch_all_sitemap_urls(sitemap_url, max_retries=5, timeout=45)
    if fetch_error:
        raise HTTPException(status_code=502, detail=fetch_error)
    if not urls:
        raise HTTPException(status_code=404, detail="No URLs found in sitemap")

    return _execute_diff(
        domain=payload.domain,
        urls=urls,
        mark_submitted=payload.mark_submitted,
        project_slug=payload.project_slug,
    )


@router.post("/diff-form", response_model=DiffResponse)
async def run_diff_form(
    domain: str = Form(...),
    sitemap_url: str = Form(""),
    mark_submitted: bool = Form(False),
    project_slug: str = Form(""),
    sitemap_file: UploadFile = File(None),
    urls_file: UploadFile = File(None),
):
    """
    Web form diff — sitemap URL, uploaded XML, or pre-expanded URLs txt.

    Input:
        domain, optional sitemap_url, sitemap_file, or urls_file (one URL per line).

    Output:
        DiffResponse (same as JSON /diff).
    """
    urls: List[str] = []
    fetch_error: Optional[str] = None

    if urls_file and urls_file.filename:
        raw = await urls_file.read()
        if not raw:
            raise HTTPException(status_code=400, detail="URLs file is empty")
        urls = _parse_urls_txt(raw)
    elif sitemap_file and sitemap_file.filename:
        raw = await sitemap_file.read()
        if not raw:
            raise HTTPException(status_code=400, detail="Uploaded sitemap file is empty")
        urls, fetch_error = parse_uploaded_sitemap_file(raw, max_retries=5, timeout=45)
    elif sitemap_url.strip():
        normalized = normalize_sitemap_url(sitemap_url)
        urls, fetch_error = fetch_all_sitemap_urls(normalized, max_retries=5, timeout=45)
    else:
        raise HTTPException(
            status_code=400,
            detail="Provide sitemap URL or upload sitemap.xml (Save As from browser)",
        )

    if fetch_error:
        raise HTTPException(status_code=502, detail=fetch_error)
    if not urls:
        raise HTTPException(status_code=404, detail="No URLs found in sitemap")

    return _execute_diff(
        domain=domain,
        urls=urls,
        mark_submitted=mark_submitted,
        project_slug=project_slug or None,
    )


def _parse_urls_txt(raw: bytes) -> List[str]:
    """Parse newline-delimited URL list from uploaded txt."""
    text = raw.decode("utf-8", errors="replace")
    urls: List[str] = []
    seen = set()
    for line in text.splitlines():
        url = line.strip()
        if not url or url.startswith("#"):
            continue
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls
