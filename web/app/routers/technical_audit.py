"""Technical SEO audit API — full site checks + Persian PDF/Excel/ZIP reports."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.seo_pdf_report import branding_defaults
from web.app.deps.auth import require_user
from web.app.services.auth_service import User, user_can_access_project
from web.app.services.file_download import resolve_download_path
from web.app.services.job_manager import job_manager
from web.app.services.technical_audit_service import (
    list_audit_reports,
    recheck_from_excel,
    run_technical_audit,
)

router = APIRouter(prefix="/api/v1/technical-audit", tags=["technical-audit"])

# Form field names that map 1:1 onto ReportBranding
_BRANDING_FORM_KEYS = (
    "report_title",
    "client_name",
    "prepared_by",
    "company_name",
    "cover_footer",
    "header_title",
    "header_subtitle",
    "section_summary",
    "section_issues",
    "section_tasks",
)


class AuditStartResponse(BaseModel):
    """Background audit job created."""

    job_id: str
    status: str
    progress_url: str


def _assert_access(user: User, project_slug: str) -> None:
    if not user_can_access_project(user.id, project_slug, is_admin=user.is_admin):
        raise HTTPException(status_code=403, detail="No access to this project")


def _branding_from_params(params: Dict[str, Any]) -> Dict[str, str]:
    """Extract branding fields from job params / form."""
    raw = params.get("branding")
    if isinstance(raw, dict):
        return {k: str(raw.get(k) or "") for k in _BRANDING_FORM_KEYS}
    return {k: str(params.get(k) or "") for k in _BRANDING_FORM_KEYS}


def _run_audit_job(job) -> None:
    """Worker thread: crawl sample, aggregate issues, render PDF/Excel/ZIP."""
    params = job.params

    def on_progress(pct: int, msg: str) -> None:
        job_manager.update_progress(job.id, pct, msg, step=msg[:48])

    result = run_technical_audit(
        params["project_slug"],
        site_url=params.get("site_url") or "",
        sitemap_url=params.get("sitemap_url") or "",
        max_pages=int(params.get("max_pages", 100)),  # 0 = full crawl
        concurrency=int(params.get("concurrency") or 6),
        timeout=int(params.get("timeout") or 20),
        link_check_limit=int(params.get("link_check_limit") or 40),
        branding=_branding_from_params(params),
        on_progress=on_progress,
    )
    job.result = result
    job.set_progress(100, "گزارش آماده شد", step="completed")


def _run_recheck_job(job) -> None:
    """
    Worker thread: parse uploaded Excel and re-check open issue rows.

    Input (job.params):
        project_slug, excel_path (temp file), optional report_id.
    """
    params = job.params

    def on_progress(pct: int, msg: str) -> None:
        job_manager.update_progress(job.id, pct, msg, step=msg[:48])

    excel_path = Path(params["excel_path"])
    try:
        result = recheck_from_excel(
            params["project_slug"],
            excel_path,
            report_id=params.get("report_id") or "",
            concurrency=int(params.get("concurrency") or 6),
            timeout=int(params.get("timeout") or 20),
            on_progress=on_progress,
        )
        job.result = result
        job.set_progress(100, result.get("notification") or "بررسی مجدد تمام شد", step="completed")
    finally:
        # Clean temp upload
        try:
            if excel_path.is_file():
                excel_path.unlink()
        except OSError:
            pass


@router.get("/branding-defaults")
def get_branding_defaults(user: User = Depends(require_user)):
    """
    Default PDF cover / header / section labels for the edit form.

    Output:
        Dict of ReportBranding field → default Persian string.
    """
    _ = user
    return {"defaults": branding_defaults()}


@router.get("/reports")
def audit_reports(project_slug: str, user: User = Depends(require_user)):
    """List previous audit reports with PDF/Excel/ZIP download links."""
    slug = project_slug.strip()
    if not slug:
        raise HTTPException(status_code=400, detail="project_slug required")
    _assert_access(user, slug)
    return {"reports": list_audit_reports(slug)}


@router.post("/start", response_model=AuditStartResponse)
async def start_audit(
    project_slug: str = Form(""),
    site_url: str = Form(""),
    sitemap_url: str = Form(""),
    max_pages: int = Form(100),
    concurrency: int = Form(6),
    timeout: int = Form(20),
    link_check_limit: int = Form(40),
    report_title: str = Form(""),
    client_name: str = Form(""),
    prepared_by: str = Form(""),
    company_name: str = Form(""),
    cover_footer: str = Form(""),
    header_title: str = Form(""),
    header_subtitle: str = Form(""),
    section_summary: str = Form(""),
    section_issues: str = Form(""),
    section_tasks: str = Form(""),
    user: User = Depends(require_user),
):
    """
    Start background technical SEO audit.

    Input:
        project_slug: Required project scope.
        site_url: Optional crawl base (may include /blog); else from domain/sitemap path.
        sitemap_url: Optional override; else uses the sitemap saved on the project.
        max_pages: Page sample size (10..5000); 0 = crawl all sitemap URLs.
        report_title / client_name / prepared_by / …: PDF branding overrides.
    """
    slug = project_slug.strip()
    if not slug:
        raise HTTPException(status_code=400, detail="project_slug required")
    _assert_access(user, slug)

    branding = {
        "report_title": report_title.strip(),
        "client_name": client_name.strip(),
        "prepared_by": prepared_by.strip(),
        "company_name": company_name.strip(),
        "cover_footer": cover_footer.strip(),
        "header_title": header_title.strip(),
        "header_subtitle": header_subtitle.strip(),
        "section_summary": section_summary.strip(),
        "section_issues": section_issues.strip(),
        "section_tasks": section_tasks.strip(),
    }

    job = job_manager.create(
        "technical_audit",
        {
            "project_slug": slug,
            "site_url": site_url.strip(),
            "sitemap_url": sitemap_url.strip(),
            "max_pages": 0 if max_pages <= 0 else max(10, min(max_pages, 5000)),
            "concurrency": max(1, min(concurrency, 12)),
            "timeout": max(5, min(timeout, 60)),
            "link_check_limit": max(0, min(link_check_limit, 200)),
            "branding": branding,
        },
        message="در صف — شروع بررسی…",
    )
    job.set_progress(2, "در صف…", step="queued")
    job_manager.enqueue(job.id, _run_audit_job)

    return AuditStartResponse(
        job_id=job.id,
        status=job.status,
        progress_url=f"/tasks/{job.id}",
    )


@router.post("/recheck", response_model=AuditStartResponse)
async def recheck_excel(
    project_slug: str = Form(""),
    report_id: str = Form(""),
    file: UploadFile = File(...),
    user: User = Depends(require_user),
):
    """
    Upload a tracking Excel and re-check rows still marked open.

    Input:
        project_slug: Project that owns the original report.
        report_id: Optional; otherwise read from Excel «شناسه گزارش».
        file: .xlsx exported by this tool (technical / content / all).

    Output:
        Background job; result includes notification + still_open_items.
    """
    slug = project_slug.strip()
    if not slug:
        raise HTTPException(status_code=400, detail="project_slug required")
    _assert_access(user, slug)

    name = (file.filename or "").lower()
    if not name.endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=400, detail="فقط فایل اکسل (.xlsx) پذیرفته می‌شود")

    # Persist upload to a temp file for the worker thread
    suffix = ".xlsx" if name.endswith(".xlsx") else ".xlsm"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp_path = Path(tmp.name)
    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="فایل خالی است")
        tmp.write(content)
        tmp.close()
    except HTTPException:
        tmp.close()
        tmp_path.unlink(missing_ok=True)
        raise
    except Exception as exc:
        tmp.close()
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    job = job_manager.create(
        "technical_audit_recheck",
        {
            "project_slug": slug,
            "report_id": report_id.strip(),
            "excel_path": str(tmp_path),
        },
        message="در صف — بررسی مجدد اکسل…",
    )
    job.set_progress(2, "در صف…", step="queued")
    job_manager.enqueue(job.id, _run_recheck_job)

    return AuditStartResponse(
        job_id=job.id,
        status=job.status,
        progress_url=f"/tasks/{job.id}",
    )


@router.get("/download")
def download_audit_file(path: str, user: User = Depends(require_user)):
    """Download audit PDF/JSON/Excel/ZIP by repo-relative path."""
    _ = user
    try:
        file_path = resolve_download_path(path)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    suffix = file_path.suffix.lower()
    media_map = {
        ".pdf": "application/pdf",
        ".json": "application/json",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xlsm": "application/vnd.ms-excel.sheet.macroEnabled.12",
        ".zip": "application/zip",
    }
    media = media_map.get(suffix, "application/octet-stream")
    return FileResponse(path=str(file_path), filename=file_path.name, media_type=media)
