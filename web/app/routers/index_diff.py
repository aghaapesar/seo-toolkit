"""Index diff API router."""

from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Form, HTTPException
from pydantic import BaseModel, Field

from src.services.url_index_tracker import UrlIndexTracker
from src.sitemap_manager import SitemapManager

router = APIRouter(prefix="/api/v1/index-diff", tags=["index-diff"])


class DiffRequest(BaseModel):
    """Request body for sitemap diff."""

    domain: str = Field(..., min_length=3)
    sitemap_url: str
    mark_submitted: bool = False


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
def import_urls(domain: str = Form(...), file_path: str = Form(...)):
    """Import previously submitted URLs from a server-local text file."""
    tracker = UrlIndexTracker(domain)
    try:
        added = tracker.import_from_txt(file_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"domain": domain, "added": added, "status": tracker.get_status()}


@router.post("/diff", response_model=DiffResponse)
def run_diff(payload: DiffRequest):
    """
    Fetch sitemap, diff against history, export txt files.

    Input: domain + sitemap URL.
    Output: counts and output file paths.
    """
    manager = SitemapManager()
    content = manager._download_with_retry(payload.sitemap_url, max_retries=3)
    if not content:
        raise HTTPException(status_code=502, detail="Failed to download sitemap")

    urls, sub_sitemaps = manager._parse_sitemap_content(content)
    if sub_sitemaps:
        urls = manager._handle_sitemap_index(sub_sitemaps)

    if not urls:
        raise HTTPException(status_code=404, detail="No URLs found in sitemap")

    tracker = UrlIndexTracker(payload.domain)
    new_urls, already_urls = tracker.diff(urls)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("output") / "index_diff" / tracker._sanitize_name(payload.domain)
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
