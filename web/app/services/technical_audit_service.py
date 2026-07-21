"""
Technical SEO audit web service — project-scoped audit + PDF report.

Input:
    project_slug or direct site URL, project sitemap (path-scoped OK), sample size.

Output:
    Audit result dict + generated PDF/JSON files with download links.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from src.services.project_manager import ProjectManager
from src.seo_pdf_report import ReportBranding, generate_seo_audit_pdf
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


def _normalize_http_url(raw: str) -> str:
    """Ensure http(s) scheme; trim trailing slash (except bare origin)."""
    url = (raw or "").strip()
    if not url:
        return ""
    if "://" not in url:
        url = f"https://{url.lstrip('/')}"
    parsed = urlparse(url)
    path = (parsed.path or "").rstrip("/")
    if path:
        return f"{parsed.scheme}://{parsed.netloc}{path}"
    return f"{parsed.scheme}://{parsed.netloc}"


def site_base_from_sitemap(sitemap_url: str) -> str:
    """
    Derive crawl base from a sitemap URL, keeping folder prefix.

    Input:
        sitemap_url: e.g. https://zitro.ir/blog/sitemap_index.xml

    Output:
        e.g. https://zitro.ir/blog  (not bare https://zitro.ir)
    """
    parsed = urlparse(_normalize_http_url(sitemap_url))
    if not parsed.netloc:
        return ""
    path = parsed.path or ""
    # Drop the sitemap filename (sitemap.xml, sitemap_index.xml, …)
    if "/" in path:
        last = path.rsplit("/", 1)[-1].lower()
        if last.endswith(".xml") or "sitemap" in last:
            path = path.rsplit("/", 1)[0]
    path = path.rstrip("/")
    if path:
        return f"{parsed.scheme}://{parsed.netloc}{path}"
    return f"{parsed.scheme}://{parsed.netloc}"


def url_in_site_scope(url: str, site_base: str) -> bool:
    """
    True when URL shares host and (if set) path prefix with site_base.

    Input:
        url: Candidate page URL from sitemap.
        site_base: Crawl scope (https://ex.com/blog).
    """
    base = urlparse(_normalize_http_url(site_base))
    candidate = urlparse(url)
    if not base.netloc or candidate.netloc != base.netloc:
        return False
    prefix = (base.path or "").rstrip("/")
    if not prefix:
        return True
    path = candidate.path or "/"
    return path == prefix or path.startswith(prefix + "/")


def resolve_audit_targets(
    project,
    *,
    site_url: str = "",
    sitemap_url: str = "",
) -> Tuple[str, str]:
    """
    Resolve crawl base + sitemap from form overrides and project settings.

    Priority for sitemap: form override → project.sitemap_url
    Priority for site: form override → project.domain (if URL/path) → folder of sitemap

    Output:
        (resolved_site_base, resolved_sitemap_url)
    """
    sm = _normalize_http_url(sitemap_url) or _normalize_http_url(project.sitemap_url or "")
    site = _normalize_http_url(site_url)

    if not site:
        domain = (project.domain or "").strip()
        if domain:
            if "://" not in domain:
                # Plain domain → origin only
                if "/" not in domain:
                    site = f"https://{domain}"
                else:
                    site = _normalize_http_url(domain)
            else:
                site = _normalize_http_url(domain)
            # If domain is bare host and sitemap has a folder, prefer sitemap folder
            d_path = urlparse(site).path
            if (not d_path or d_path == "/") and sm:
                from_sm = site_base_from_sitemap(sm)
                if urlparse(from_sm).path:
                    site = from_sm
        elif sm:
            site = site_base_from_sitemap(sm)

    if not site and not sm:
        raise ValueError("Site URL or project sitemap is required")
    if not site and sm:
        site = site_base_from_sitemap(sm)
    if not sm and site:
        # Fall back to common root sitemap under the resolved host
        p = urlparse(site)
        sm = f"{p.scheme}://{p.netloc}/sitemap.xml"

    return site, sm


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
                    "sitemap_url": data.get("sitemap_url", ""),
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
    sitemap_url: str = "",
    max_pages: int = 100,
    concurrency: int = 6,
    timeout: int = 20,
    link_check_limit: int = 40,
    branding: Optional[Dict[str, Any]] = None,
    on_progress: Optional[Callable[[int, str], None]] = None,
) -> Dict[str, Any]:
    """
    Run full technical audit and write PDF + JSON report.

    Input:
        project_slug: Project scope (sitemap + output dir).
        site_url: Optional crawl base override (may include /blog path).
        sitemap_url: Optional sitemap override; else project.sitemap_url.
        max_pages: Page sample cap (10..5000); 0 = crawl all sitemap URLs.
        branding: Optional PDF cover/header/section label overrides.

    Output:
        Result dict with files list for job.result.
    """
    manager = ProjectManager()
    project = manager.get_project(project_slug)
    if not project:
        raise ValueError(f"Project not found: {project_slug}")

    resolved_site, resolved_sitemap = resolve_audit_targets(
        project, site_url=site_url, sitemap_url=sitemap_url
    )

    # Collect URLs from the project's configured sitemap (not domain-root guess)
    urls: List[str] = []
    sitemap_error: Optional[str] = None
    if resolved_sitemap:
        if on_progress:
            on_progress(3, f"دریافت sitemap پروژه: {resolved_sitemap}")
        try:
            from web.app.services.sitemap_fetch import fetch_all_sitemap_urls

            raw, error, _src = fetch_all_sitemap_urls(resolved_sitemap, timeout=timeout)
            sitemap_error = error
            if not error and raw:
                urls = [u for u in raw if url_in_site_scope(u, resolved_site)]
                if not urls and raw:
                    # Scope was too tight — keep same-host URLs as fallback
                    host = urlparse(resolved_site).netloc
                    urls = [u for u in raw if urlparse(u).netloc == host]
                    logger.warning(
                        "No URLs under path scope %s; falling back to host filter (%s urls)",
                        resolved_site,
                        len(urls),
                    )
            elif error:
                logger.warning("Sitemap fetch error for %s: %s", resolved_sitemap, error)
        except Exception as exc:
            sitemap_error = str(exc)
            logger.warning("Sitemap fetch failed, auditing homepage only: %s", exc)

    # max_pages == 0 → full crawl (auditor caps at ABSOLUTE_PAGE_CAP)
    effective_pages = 0 if max_pages <= 0 else max(10, min(max_pages, 5000))
    auditor = TechnicalSeoAuditor(
        resolved_site,
        urls,
        max_pages=effective_pages,
        timeout=max(5, timeout),
        concurrency=max(1, min(concurrency, 12)),
        link_check_limit=max(0, min(link_check_limit, 200)),
        configured_sitemap_url=resolved_sitemap,
    )
    result = auditor.run(on_progress=on_progress)
    result["sitemap_url"] = resolved_sitemap
    result["sitemap_url_count"] = len(urls)
    if sitemap_error:
        result["sitemap_fetch_error"] = sitemap_error

    report_branding = ReportBranding.from_dict(branding).resolved(
        project_name=project.name or project_slug,
        site_url=resolved_site,
    )
    result["branding"] = report_branding.to_dict()

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
    generate_seo_audit_pdf(
        result,
        pdf_path,
        project_name=project.name or project_slug,
        branding=report_branding,
    )

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
