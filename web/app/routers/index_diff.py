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
from web.app.services.sitemap_fetch import fetch_all_sitemap_urls, normalize_sitemap_url

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

    tracker = UrlIndexTracker(payload.domain)
    if payload.project_slug:
        project, paths = resolve_project_paths(payload.project_slug)
        tracker = UrlIndexTracker(
            project.domain,
            base_dir=str(paths.index_history_dir),
            flat=True,
        )
        output_dir = paths.output_dir / "index_diff"
    else:
        output_dir = Path("output") / "index_diff" / tracker._sanitize_name(payload.domain)

    new_urls, already_urls = tracker.diff(urls)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_file = tracker.export_txt(new_urls, output_dir / f"new_urls_{stamp}.txt")
    already_file = tracker.export_txt(
        already_urls, output_dir / f"already_submitted_{stamp}.txt"
    )

    batch_id = None
    if payload.mark_submitted and new_urls:
        batch_id = tracker.mark_batch_submitted(new_urls, source_file=new_file.name)

    return DiffResponse(
        domain=payload.domain,
        total=len(urls),
        new_count=len(new_urls),
        already_count=len(already_urls),
        new_file=str(new_file),
        already_file=str(already_file),
        batch_id=batch_id,
    )
