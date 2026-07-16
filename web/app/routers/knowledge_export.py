"""Knowledge export API — RAG Markdown export from sitemap."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from web.app.deps.auth import require_user
from web.app.services.auth_service import User, user_can_access_project
from web.app.services.job_manager import job_manager
from web.app.services.knowledge_export_store import list_pages
from web.app.services.knowledge_export_service import (
    analyze_project_sitemap,
    build_zip_archive,
    get_dashboard,
    resolve_export_download,
    run_knowledge_export,
    test_export_model,
)

router = APIRouter(prefix="/api/v1/knowledge-export", tags=["knowledge-export"])


class ExportStartResponse(BaseModel):
    """Background export job created."""

    job_id: str
    status: str
    progress_url: str


class ZipDownloadRequest(BaseModel):
    """Multi-file ZIP download request."""

    project_slug: str
    paths: list[str]


def _assert_access(user: User, project_slug: str) -> None:
    if not user_can_access_project(user.id, project_slug, is_admin=user.is_admin):
        raise HTTPException(status_code=403, detail="No access to this project")


def _run_export_job(job) -> None:
    """Worker thread for knowledge export."""
    slug = job.params.get("project_slug", "")

    def on_progress(processed: int, total: int, message: str) -> None:
        pct = int((processed / max(total, 1)) * 95) if total else 5
        job_manager.update_progress(job.id, pct, message, step="export")

    result = run_knowledge_export(
        slug,
        sitemap_url=job.params.get("sitemap_url") or "",
        analysis_id=job.params.get("analysis_id") or "",
        selected_segment_ids=job.params.get("selected_segments") or [],
        model_name=job.params.get("model_name") or "",
        use_llm=bool(job.params.get("use_llm", True)),
        include_blog=bool(job.params.get("include_blog")),
        include_noindex=bool(job.params.get("include_noindex")),
        product_sample_limit=int(job.params.get("product_sample_limit") or 0),
        write_parts=bool(job.params.get("write_parts", True)),
        skip_unchanged=bool(job.params.get("skip_unchanged", True)),
        max_part_kb=int(job.params.get("max_part_kb") or 500),
        max_pages_per_part=int(job.params.get("max_pages_per_part") or 50),
        include_pattern=job.params.get("include_pattern") or None,
        exclude_pattern=job.params.get("exclude_pattern") or None,
        concurrency=int(job.params.get("concurrency") or 4),
        rate_limit_seconds=float(job.params.get("rate_limit") or 0.25),
        timeout=int(job.params.get("timeout") or 45),
        max_retries=int(job.params.get("max_retries") or 3),
        min_content_chars=int(job.params.get("min_chars") or 100),
        on_progress=on_progress,
    )
    job.result = result
    job.set_progress(100, "Export complete", step="completed")


@router.get("/dashboard")
def export_dashboard(project_slug: str, user: User = Depends(require_user)):
    """Latest export stats, registry, and downloadable files for a project."""
    slug = project_slug.strip()
    if not slug:
        raise HTTPException(status_code=400, detail="project_slug required")
    _assert_access(user, slug)
    return get_dashboard(slug)


@router.get("/registry")
def export_registry(project_slug: str, user: User = Depends(require_user)):
    """List SQLite registry rows for per-URL export state."""
    slug = project_slug.strip()
    if not slug:
        raise HTTPException(status_code=400, detail="project_slug required")
    _assert_access(user, slug)
    return {"pages": list_pages(slug)}


@router.post("/test-model")
async def test_model(
    model_name: str = Form(""),
    user: User = Depends(require_user),
):
    """Test AI model connection before starting export."""
    _ = user
    result = test_export_model(model_name)
    if not result.get("connected"):
        raise HTTPException(status_code=400, detail=result.get("error") or "Connection failed")
    return result


@router.post("/analyze")
async def analyze_sitemap(
    project_slug: str = Form(""),
    sitemap_url: str = Form(""),
    user: User = Depends(require_user),
):
    """
    Phase 1: fetch sitemap and return content segments for selection.

    Output:
        analysis_id, segments, staleness report.
    """
    slug = project_slug.strip()
    if not slug:
        raise HTTPException(status_code=400, detail="project_slug required")
    _assert_access(user, slug)
    try:
        return analyze_project_sitemap(slug, sitemap_url=sitemap_url.strip())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/start", response_model=ExportStartResponse)
async def start_export(
    project_slug: str = Form(""),
    sitemap_url: str = Form(""),
    analysis_id: str = Form(""),
    selected_segments: str = Form("[]"),
    model_name: str = Form(""),
    use_llm: str = Form("true"),
    include_blog: str = Form("false"),
    include_noindex: str = Form("false"),
    product_sample_limit: int = Form(0),
    write_parts: str = Form("true"),
    skip_unchanged: str = Form("true"),
    max_part_kb: int = Form(500),
    max_pages_per_part: int = Form(50),
    include_pattern: str = Form(""),
    exclude_pattern: str = Form(""),
    concurrency: int = Form(4),
    rate_limit: float = Form(0.25),
    timeout: int = Form(45),
    max_retries: int = Form(3),
    min_chars: int = Form(100),
    user: User = Depends(require_user),
):
    """
    Start knowledge export as background job.

    Input:
        project_slug, segments, model, RAG options.
    """
    slug = project_slug.strip()
    if not slug:
        raise HTTPException(status_code=400, detail="project_slug required")
    _assert_access(user, slug)

    seg_ids: list[str] = []
    if selected_segments.strip():
        try:
            parsed = json.loads(selected_segments)
            if isinstance(parsed, list):
                seg_ids = [str(x) for x in parsed if x]
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="Invalid selected_segments JSON") from exc

    if not analysis_id.strip():
        raise HTTPException(
            status_code=400,
            detail="Run sitemap analysis first and select segments",
        )
    if not seg_ids:
        raise HTTPException(status_code=400, detail="Select at least one segment")

    use_llm_flag = use_llm.lower() not in ("false", "0", "no")
    if use_llm_flag:
        test_result = test_export_model(model_name)
        if not test_result.get("connected"):
            raise HTTPException(
                status_code=400,
                detail=test_result.get("error") or "AI model connection test failed",
            )

    job = job_manager.create(
        "knowledge_export",
        {
            "project_slug": slug,
            "sitemap_url": sitemap_url.strip(),
            "analysis_id": analysis_id.strip(),
            "selected_segments": seg_ids,
            "model_name": model_name.strip(),
            "use_llm": use_llm_flag,
            "include_blog": include_blog.lower() in ("true", "1", "yes"),
            "include_noindex": include_noindex.lower() in ("true", "1", "yes"),
            "product_sample_limit": max(0, product_sample_limit),
            "write_parts": write_parts.lower() not in ("false", "0", "no"),
            "skip_unchanged": skip_unchanged.lower() not in ("false", "0", "no"),
            "max_part_kb": max(64, min(max_part_kb, 2048)),
            "max_pages_per_part": max(1, min(max_pages_per_part, 200)),
            "include_pattern": include_pattern.strip(),
            "exclude_pattern": exclude_pattern.strip(),
            "concurrency": max(1, min(concurrency, 16)),
            "rate_limit": max(0.0, rate_limit),
            "timeout": max(10, timeout),
            "max_retries": max(1, max_retries),
            "min_chars": max(0, min_chars),
        },
        message="Queued — fetching sitemap…",
    )
    job.set_progress(2, "Queued…", step="queued")
    job_manager.enqueue(job.id, _run_export_job)

    return ExportStartResponse(
        job_id=job.id,
        status=job.status,
        progress_url=f"/tasks/{job.id}",
    )


@router.post("/download-zip")
async def download_zip(payload: ZipDownloadRequest, user: User = Depends(require_user)):
    """Download multiple export files as ZIP with folder structure."""
    slug = payload.project_slug.strip()
    if not slug:
        raise HTTPException(status_code=400, detail="project_slug required")
    _assert_access(user, slug)
    if not payload.paths:
        raise HTTPException(status_code=400, detail="No files selected")
    try:
        buffer = build_zip_archive(slug, payload.paths)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="knowledge_export.zip"'},
    )


@router.get("/download")
def download_export_file(
    path: str,
    project_slug: str = "",
    user: User = Depends(require_user),
):
    """
    Download export file by repo-relative path.

    Input:
        path: File under projects/ or output/.
        project_slug: Optional — marks first download in registry.
    """
    slug = project_slug.strip()
    if slug:
        _assert_access(user, slug)
    try:
        file_path = resolve_export_download(path, project_slug=slug)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type="application/octet-stream",
    )
