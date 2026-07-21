"""
Technical SEO audit web service — project-scoped audit + PDF report.

Input:
    project_slug or direct site URL, sample size options.

Output:
    Audit result dict + generated PDF/JSON files with download links.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse

from src.services.project_manager import ProjectManager
from src.seo_pdf_report import generate_seo_audit_pdf
from src.technical_seo_audit import TechnicalSeoAuditor
from web.app.services.file_download import _relative_to_root

logger = logging.getLogger(__name__)


def audit_output_dir(project_slug: str) -> Path:
    """Resolve output dir projects/{slug}/output/technical_audit/."""
    paths = ProjectManager().get_paths(project_slug)
    return paths.output_dir / "technical_audit"


def _download_entry(label: str, path: Path) -> Dict[str, str]:
    """Downloadable file descriptor for UI."""
    rel = _relative_to_root(path)
    return {
        "label": label,
        "name": path.name,
        "path": rel,
        "download_url": f"/api/v1/technical-audit/download?path={rel}",
    }


def list_audit_reports(project_slug: str) -> List[Dict[str, Any]]:
    """
    List previous audit reports (newest first).

    Output:
        Entries with pdf/json download links and summary metadata.
    """
    out_dir = audit_output_dir(project_slug)
    if not out_dir.is_dir():
        return []
    reports: List[Dict[str, Any]] = []
    for json_path in sorted(out_dir.glob("audit_*.json"), reverse=True):
        entry: Dict[str, Any] = {"json": _download_entry(json_path.name, json_path)}
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            entry.update(
                {
                    "site_url": data.get("site_url", ""),
                    "generated_at": data.get("generated_at", ""),
                    "score": data.get("score"),
                    "pages_checked": data.get("pages_checked"),
                    "issue_count": len(data.get("issues") or []),
                    "severity_counts": data.get("severity_counts") or {},
                }
            )
        except (json.JSONDecodeError, OSError):
            pass
        pdf_path = json_path.with_suffix(".pdf")
        if pdf_path.is_file():
            entry["pdf"] = _download_entry(pdf_path.name, pdf_path)
        reports.append(entry)
    return reports[:20]


def run_technical_audit(
    project_slug: str,
    *,
    site_url: str = "",
    max_pages: int = 100,
    concurrency: int = 6,
    timeout: int = 20,
    link_check_limit: int = 40,
    on_progress: Optional[Callable[[int, str], None]] = None,
) -> Dict[str, Any]:
    """
    Run full technical audit and write PDF + JSON report.

    Input:
        project_slug: Project scope (sitemap + output dir).
        site_url: Optional override; else derived from project sitemap.
        max_pages: Page sample cap (10..5000); 0 = crawl all sitemap URLs.

    Output:
        Result dict with files list for job.result.
    """
    manager = ProjectManager()
    project = manager.get_project(project_slug)
    if not project:
        raise ValueError(f"Project not found: {project_slug}")

    resolved_site = site_url.strip()
    sitemap_url = (project.sitemap_url or "").strip()
    if not resolved_site:
        if not sitemap_url:
            raise ValueError("Site URL or project sitemap is required")
        p = urlparse(sitemap_url)
        resolved_site = f"{p.scheme or 'https'}://{p.netloc}"

    # Collect sample URLs from sitemap when available
    urls: List[str] = []
    if sitemap_url:
        if on_progress:
            on_progress(3, "دریافت sitemap…")
        try:
            from web.app.services.sitemap_fetch import fetch_all_sitemap_urls

            raw, error, _src = fetch_all_sitemap_urls(sitemap_url, timeout=timeout)
            if not error and raw:
                host = urlparse(resolved_site).netloc
                urls = [u for u in raw if urlparse(u).netloc == host]
        except Exception as exc:
            logger.warning("Sitemap fetch failed, auditing homepage links only: %s", exc)

    # max_pages == 0 → full crawl (auditor caps at ABSOLUTE_PAGE_CAP)
    effective_pages = 0 if max_pages <= 0 else max(10, min(max_pages, 5000))
    auditor = TechnicalSeoAuditor(
        resolved_site,
        urls,
        max_pages=effective_pages,
        timeout=max(5, timeout),
        concurrency=max(1, min(concurrency, 12)),
        link_check_limit=max(0, min(link_check_limit, 200)),
    )
    result = auditor.run(on_progress=on_progress)

    # Persist JSON + PDF
    out_dir = audit_output_dir(project_slug)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_host = re.sub(r"[^a-z0-9.-]+", "-", urlparse(resolved_site).netloc.lower())
    base = out_dir / f"audit_{safe_host}_{stamp}"

    json_path = base.with_suffix(".json")
    json_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if on_progress:
        on_progress(96, "ساخت گزارش PDF…")
    pdf_path = base.with_suffix(".pdf")
    generate_seo_audit_pdf(result, pdf_path, project_name=project.name or project_slug)

    files = [
        _download_entry("گزارش PDF", pdf_path),
        _download_entry("داده JSON", json_path),
    ]
    result_out = dict(result)
    result_out.update(
        {
            "project_slug": project_slug,
            "files": files,
            "pdf_path": _relative_to_root(pdf_path),
        }
    )
    if on_progress:
        on_progress(100, "گزارش آماده شد")
    return result_out
