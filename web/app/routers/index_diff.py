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
        mark_submitted: Whether to mark new URLs as submitted.
        project_slug: Optional isolated project folder.

    Output:
        DiffResponse with counts and file paths.
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

    new_urls, already_urls = tracker.diff(urls)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_file = tracker.export_txt(new_urls, output_dir / f"new_urls_{stamp}.txt")
    already_file = tracker.export_txt(
        already_urls, output_dir / f"already_submitted_{stamp}.txt"
    )

    batch_id = None
    if mark_submitted and new_urls:
        batch_id = tracker.mark_batch_submitted(new_urls, source_file=new_file.name)

    return DiffResponse(
        domain=domain,
        total=len(urls),
        new_count=len(new_urls),
        already_count=len(already_urls),
        new_file=str(new_file),
        already_file=str(already_file),
        batch_id=batch_id,
    )


@router.get("/status/{domain}")
def get_status(domain: str):
    """Return submitted URL statistics for a domain."""
    tracker = UrlIndexTracker(domain)
    return tracker.get_status()


@router.post("/import")
async def import_urls(
    domain: str = Form(...),
    urls_files: List[UploadFile] = File(...),
    project_slug: str = Form(""),
):
    """Import submitted URLs from one or more uploaded txt files."""
    if not urls_files:
        raise HTTPException(status_code=400, detail="At least one .txt file is required")

    saved_paths: List[str] = []
    for upload in urls_files:
        if not upload.filename:
            continue
        saved_paths.append(str(_save_upload(upload, "import")))

    if not saved_paths:
        raise HTTPException(status_code=400, detail="No valid files received")

    if project_slug:
        project, paths = resolve_project_paths(project_slug)
        tracker = UrlIndexTracker(
            project.domain,
            base_dir=str(paths.index_history_dir),
            flat=True,
        )
        domain = project.domain
    else:
        tracker = UrlIndexTracker(domain)

    result = tracker.import_from_txt_files(saved_paths)
    return {
        "domain": domain,
        "added": result["total_added"],
        "files_processed": result["files_processed"],
        "files": result["files"],
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
):
    """
    Web form diff — sitemap URL and/or uploaded sitemap.xml file.

    Input:
        domain, optional sitemap_url, optional sitemap_file upload.

    Output:
        DiffResponse (same as JSON /diff).
    """
    urls: List[str] = []
    fetch_error: Optional[str] = None

    if sitemap_file and sitemap_file.filename:
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
