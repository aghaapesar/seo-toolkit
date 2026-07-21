"""Technical SEO audit API — full site checks + Persian PDF report."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from web.app.deps.auth import require_user
from web.app.services.auth_service import User, user_can_access_project
from web.app.services.file_download import resolve_download_path
from web.app.services.job_manager import job_manager
from web.app.services.technical_audit_service import (
    list_audit_reports,
    run_technical_audit,
)

router = APIRouter(prefix="/api/v1/technical-audit", tags=["technical-audit"])


class AuditStartResponse(BaseModel):
    """Background audit job created."""

    job_id: str
    status: str
    progress_url: str


def _assert_access(user: User, project_slug: str) -> None:
    if not user_can_access_project(user.id, project_slug, is_admin=user.is_admin):
        raise HTTPException(status_code=403, detail="No access to this project")


def _run_audit_job(job) -> None:
    """Worker thread: crawl sample, aggregate issues, render PDF."""
    params = job.params

    def on_progress(pct: int, msg: str) -> None:
        job_manager.update_progress(job.id, pct, msg, step=msg[:48])

    result = run_technical_audit(
        params["project_slug"],
        site_url=params.get("site_url") or "",
        max_pages=int(params.get("max_pages", 100)),  # 0 = full crawl
        concurrency=int(params.get("concurrency") or 6),
        timeout=int(params.get("timeout") or 20),
        link_check_limit=int(params.get("link_check_limit") or 40),
        on_progress=on_progress,
    )
    job.result = result
    job.set_progress(100, "گزارش آماده شد", step="completed")


@router.get("/reports")
def audit_reports(project_slug: str, user: User = Depends(require_user)):
    """List previous audit reports with download links."""
    slug = project_slug.strip()
    if not slug:
        raise HTTPException(status_code=400, detail="project_slug required")
    _assert_access(user, slug)
    return {"reports": list_audit_reports(slug)}


@router.post("/start", response_model=AuditStartResponse)
async def start_audit(
    project_slug: str = Form(""),
    site_url: str = Form(""),
    max_pages: int = Form(100),
    concurrency: int = Form(6),
    timeout: int = Form(20),
    link_check_limit: int = Form(40),
    user: User = Depends(require_user),
):
    """
    Start background technical SEO audit.

    Input:
        project_slug: Required project scope.
        site_url: Optional homepage override (else from project sitemap).
        max_pages: Page sample size (10..5000); 0 = crawl all sitemap URLs.
    """
    slug = project_slug.strip()
    if not slug:
        raise HTTPException(status_code=400, detail="project_slug required")
    _assert_access(user, slug)

    job = job_manager.create(
        "technical_audit",
        {
            "project_slug": slug,
            "site_url": site_url.strip(),
            "max_pages": 0 if max_pages <= 0 else max(10, min(max_pages, 5000)),
            "concurrency": max(1, min(concurrency, 12)),
            "timeout": max(5, min(timeout, 60)),
            "link_check_limit": max(0, min(link_check_limit, 200)),
        },
        message="در صف — شروع ممیزی…",
    )
    job.set_progress(2, "در صف…", step="queued")
    job_manager.enqueue(job.id, _run_audit_job)

    return AuditStartResponse(
        job_id=job.id,
        status=job.status,
        progress_url=f"/tasks/{job.id}",
    )


@router.get("/download")
def download_audit_file(path: str, user: User = Depends(require_user)):
    """Download audit PDF/JSON by repo-relative path."""
    _ = user
    try:
        file_path = resolve_download_path(path)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    media = "application/pdf" if file_path.suffix == ".pdf" else "application/octet-stream"
    return FileResponse(path=str(file_path), filename=file_path.name, media_type=media)
