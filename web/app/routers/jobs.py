"""Background job API — start tasks, poll progress, receive client-side data."""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from web.app.routers.index_diff import _execute_diff, _parse_urls_txt
from web.app.services.job_manager import JobRecord, job_manager
from web.app.services.sitemap_fetch import (
    fetch_all_sitemap_urls,
    parse_uploaded_sitemap_file,
)

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


class ProgressUpdate(BaseModel):
    """Client-reported progress while work runs in the browser."""

    progress: int = Field(..., ge=0, le=100)
    message: str = ""
    step: Optional[str] = None


def _resolve_index_diff_urls(job: JobRecord) -> list[str]:
    """
    Build URL list for an index_diff job from stored params.

    Input:
        job: Job with urls, uploaded file path, or sitemap_url.

    Output:
        Deduplicated URL list.

    Raises:
        ValueError: When no URLs could be resolved.
    """
    if job.params.get("urls"):
        return list(job.params["urls"])

    file_path = job.params.get("sitemap_file_path")
    if file_path:
        raw = Path(file_path).read_bytes()
        urls, fetch_error = parse_uploaded_sitemap_file(raw, max_retries=5, timeout=60)
        if fetch_error:
            raise ValueError(fetch_error)
        if not urls:
            raise ValueError("No URLs found in uploaded sitemap")
        return urls

    sitemap_url = (job.params.get("sitemap_url") or "").strip()
    if sitemap_url:
        urls, fetch_error = fetch_all_sitemap_urls(sitemap_url, max_retries=5, timeout=60)
        if fetch_error:
            raise ValueError(fetch_error)
        if not urls:
            raise ValueError("No URLs found in sitemap")
        return urls

    raise ValueError("No sitemap data supplied for this job")


def _run_index_diff_job(job: JobRecord) -> None:
    """Worker: resolve URLs then run tracker diff."""
    job.set_progress(55, job.message or "Resolving sitemap URLs…", step="resolve_urls")
    urls = _resolve_index_diff_urls(job)
    job.set_progress(
        75,
        f"Comparing {len(urls)} URLs…",
        step="diff",
    )
    result = _execute_diff(
        domain=job.params["domain"],
        urls=urls,
        mark_submitted=bool(job.params.get("mark_submitted")),
        project_slug=job.params.get("project_slug") or None,
    )
    job.result = result.model_dump()
    job.set_progress(100, "Done", step="completed")


@router.get("/{job_id}")
def get_job(job_id: str):
    """Poll job status, progress, and result."""
    job = job_manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_dict()


@router.post("/{job_id}/progress")
def update_job_progress(job_id: str, payload: ProgressUpdate):
    """Allow browser clients to report sitemap download progress."""
    job = job_manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status in ("completed", "failed"):
        return job.to_dict()
    job_manager.update_progress(
        job_id,
        payload.progress,
        payload.message,
        step=payload.step,
    )
    return job_manager.require(job_id).to_dict()


@router.post("/{job_id}/supply-urls")
async def supply_urls(job_id: str, urls_file: UploadFile = File(...)):
    """
    Receive expanded URL list from browser after recursive sitemap fetch.

    Input:
        urls_file: Newline-delimited URLs (txt).

    Output:
        Updated job; server diff starts in background.
    """
    job = job_manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.job_type != "index_diff":
        raise HTTPException(status_code=400, detail="Job type does not accept URLs")

    raw = await urls_file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="URLs file is empty")
    urls = _parse_urls_txt(raw)
    if not urls:
        raise HTTPException(status_code=400, detail="No URLs found in uploaded list")

    job.params["urls"] = urls
    job.status = "queued"
    job.set_progress(50, f"Loaded {len(urls)} URLs from sitemap", step="urls_ready")
    job_manager.enqueue(job_id, _run_index_diff_job)
    return job.to_dict()


@router.post("/index-diff/start")
async def start_index_diff_job(
    domain: str = Form(...),
    sitemap_url: str = Form(""),
    mark_submitted: bool = Form(False),
    project_slug: str = Form(""),
    sitemap_file: UploadFile = File(None),
):
    """
    Create an index-diff background job and return its id.

    Input:
        domain, optional sitemap_url or sitemap_file upload.

    Output:
        job_id + initial status (waiting_client when browser must fetch).
    """
    from web.app.routers.index_diff import _save_upload
    from web.app.services.sitemap_fetch import normalize_sitemap_url

    params = {
        "domain": domain.strip(),
        "mark_submitted": mark_submitted,
        "project_slug": (project_slug or "").strip() or None,
    }

    initial_status = "waiting_client"
    message = "Waiting for sitemap processing…"

    if sitemap_file and sitemap_file.filename:
        dest = _save_upload(sitemap_file, "job_sitemap")
        params["sitemap_file_path"] = str(dest)
        initial_status = "queued"
        message = "Queued — parsing uploaded sitemap…"
    elif sitemap_url.strip():
        params["sitemap_url"] = normalize_sitemap_url(sitemap_url)
        initial_status = "waiting_client"
        message = "Waiting — fetching sitemap in browser…"
    else:
        raise HTTPException(
            status_code=400,
            detail="Provide sitemap URL or upload sitemap.xml",
        )

    job = job_manager.create(
        "index_diff",
        params,
        initial_status=initial_status,
        message=message,
    )
    job.set_progress(5, message, step="created")

    if initial_status == "queued":
        job_manager.enqueue(job.id, _run_index_diff_job)

    return {
        "job_id": job.id,
        "status": job.status,
        "progress_url": f"/tasks/{job.id}",
    }
