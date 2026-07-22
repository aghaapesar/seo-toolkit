"""
Technical SEO audit web service — project-scoped audit + PDF/Excel/ZIP reports.

Input:
    project_slug or direct site URL, project sitemap (path-scoped OK), sample size.

Output:
    Audit result dict + persisted PDF/JSON/Excel/ZIP with download links.
    Report history kept under projects/{slug}/output/technical_audit/ (unique stamp).
"""

from __future__ import annotations

import json
import logging
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

from src.seo_audit_excel import (
    generate_audit_excels,
    open_issue_pairs,
    parse_status_workbook,
)
from src.seo_pdf_report import ReportBranding, generate_seo_audit_pdf
from src.services.project_manager import ProjectManager
from src.technical_seo_audit import TechnicalSeoAuditor
from web.app.services.file_download import _relative_to_root

logger = logging.getLogger(__name__)

EXCEL_LABELS = {
    "technical": "اکسل تیم فنی",
    "content": "اکسل تیم محتوا",
    "all": "اکسل همه مشکلات",
}


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


def _safe_report_stem(site_url: str, stamp: str) -> str:
    """
    Build a unique report filename stem without pathlib suffix traps.

    Input:
        site_url: Audited site (may contain dots like zitro.ir).
        stamp: UTC timestamp string YYYYMMDD_HHMMSS.

    Output:
        e.g. audit_zitro-ir_20260721_154234  (dots → hyphens so .json is not lost).
    """
    host = urlparse(site_url).netloc.lower() or "site"
    safe_host = re.sub(r"[^a-z0-9]+", "-", host).strip("-") or "site"
    return f"audit_{safe_host}_{stamp}"


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
                if "/" not in domain:
                    site = f"https://{domain}"
                else:
                    site = _normalize_http_url(domain)
            else:
                site = _normalize_http_url(domain)
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
        p = urlparse(site)
        sm = f"{p.scheme}://{p.netloc}/sitemap.xml"

    return site, sm


def _reports_index_path(project_slug: str) -> Path:
    """Path to durable reports_index.json for this project."""
    return audit_output_dir(project_slug) / "reports_index.json"


def _load_reports_index(project_slug: str) -> List[Dict[str, Any]]:
    """Load durable report registry (empty list if missing/corrupt)."""
    path = _reports_index_path(project_slug)
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return list(data.get("reports") or []) if isinstance(data, dict) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_reports_index(project_slug: str, reports: List[Dict[str, Any]]) -> None:
    """Persist report registry (newest first, capped)."""
    out_dir = audit_output_dir(project_slug)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = _reports_index_path(project_slug)
    trimmed = reports[:50]
    path.write_text(
        json.dumps({"reports": trimmed}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _append_report_index(project_slug: str, meta: Dict[str, Any]) -> None:
    """Insert a new report at the front of the durable index."""
    existing = [
        r
        for r in _load_reports_index(project_slug)
        if r.get("report_id") != meta.get("report_id")
    ]
    existing.insert(0, meta)
    _save_reports_index(project_slug, existing)


def _sidecar_files(out_dir: Path, report_id: str) -> Dict[str, Path]:
    """
    Discover artifact files for a report stem.

    Output:
        Keys: json, pdf, zip, excel_technical, excel_content, excel_all (when present).
    """
    found: Dict[str, Path] = {}
    json_path = out_dir / f"{report_id}.json"
    pdf_path = out_dir / f"{report_id}.pdf"
    zip_path = out_dir / f"{report_id}_package.zip"
    if json_path.is_file():
        found["json"] = json_path
    if pdf_path.is_file():
        found["pdf"] = pdf_path
    if zip_path.is_file():
        found["zip"] = zip_path
    for key, suffix in (
        ("excel_technical", "_فنی.xlsx"),
        ("excel_content", "_محتوا.xlsx"),
        ("excel_all", "_همه.xlsx"),
    ):
        p = out_dir / f"{report_id}{suffix}"
        if p.is_file():
            found[key] = p
    return found


def _build_report_entry(
    project_slug: str, report_id: str, data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build list-API entry with all download links for one report.

    Input:
        project_slug / report_id: Locate files under technical_audit/.
        data: Optional already-loaded JSON body.
    """
    out_dir = audit_output_dir(project_slug)
    files = _sidecar_files(out_dir, report_id)
    entry: Dict[str, Any] = {
        "report_id": report_id,
        "project_slug": project_slug,
    }
    if data is None and "json" in files:
        try:
            data = json.loads(files["json"].read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
    data = data or {}
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
    if "json" in files:
        entry["json"] = _download_entry("داده JSON", files["json"])
    if "pdf" in files:
        entry["pdf"] = _download_entry("گزارش PDF", files["pdf"])
    if "zip" in files:
        entry["package"] = _download_entry("پکیج کامل (ZIP)", files["zip"])
    excels = []
    for key, label in (
        ("excel_technical", EXCEL_LABELS["technical"]),
        ("excel_content", EXCEL_LABELS["content"]),
        ("excel_all", EXCEL_LABELS["all"]),
    ):
        if key in files:
            dl = _download_entry(label, files[key])
            entry[key] = dl
            excels.append(dl)
    if excels:
        entry["excels"] = excels
    return entry


def list_audit_reports(project_slug: str) -> List[Dict[str, Any]]:
    """
    List previous audit reports (newest first), from index + disk scan.

    Output:
        Entries with pdf/json/excel/zip download links and summary metadata.
    """
    out_dir = audit_output_dir(project_slug)
    if not out_dir.is_dir():
        return []

    seen: Set[str] = set()
    ordered_ids: List[str] = []
    for meta in _load_reports_index(project_slug):
        rid = str(meta.get("report_id") or "")
        if rid and rid not in seen:
            seen.add(rid)
            ordered_ids.append(rid)

    for json_path in sorted(out_dir.glob("audit_*.json"), reverse=True):
        rid = json_path.stem
        if rid not in seen:
            seen.add(rid)
            ordered_ids.append(rid)

    reports = [_build_report_entry(project_slug, rid) for rid in ordered_ids]
    reports.sort(key=lambda r: str(r.get("generated_at") or ""), reverse=True)
    return reports[:30]


def _build_package_zip(
    report_id: str,
    out_dir: Path,
    artifact_paths: List[Path],
) -> Path:
    """
    Bundle PDF + JSON + Excels into one ZIP package.

    Output:
        Path to {report_id}_package.zip
    """
    zip_path = out_dir / f"{report_id}_package.zip"
    readme = (
        "Seo Toolkit — بسته گزارش بررسی مشکلات فنی\n"
        f"report_id: {report_id}\n\n"
        "محتویات:\n"
        "- PDF: گزارش مدیریتی فارسی\n"
        "- JSON: داده خام برای آرشیو\n"
        "- اکسل فنی / محتوا / همه: پیگیری تسک‌ها (ستون وضعیت را تیک بزنید)\n\n"
        "پس از اصلاح، اکسل را دوباره در ابزار آپلود کنید تا موارد باز بررسی شوند.\n"
    )
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("README.txt", readme)
        for path in artifact_paths:
            if path.is_file():
                zf.write(path, arcname=path.name)
    return zip_path


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
    Run full technical audit and write PDF + JSON + Excel + ZIP report.

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

    out_dir = audit_output_dir(project_slug)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_id = _safe_report_stem(resolved_site, stamp)
    result["report_id"] = report_id

    json_path = out_dir / f"{report_id}.json"
    json_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if on_progress:
        on_progress(96, "ساخت گزارش PDF…")
    pdf_path = out_dir / f"{report_id}.pdf"
    generate_seo_audit_pdf(
        result,
        pdf_path,
        project_name=project.name or project_slug,
        branding=report_branding,
    )

    if on_progress:
        on_progress(97, "ساخت فایل‌های اکسل پیگیری…")
    excel_paths = generate_audit_excels(result, out_dir, report_id)

    artifact_paths: List[Path] = [pdf_path, json_path, *excel_paths.values()]
    if on_progress:
        on_progress(98, "بسته‌بندی پکیج ZIP…")
    zip_path = _build_package_zip(report_id, out_dir, artifact_paths)

    files = [
        _download_entry("پکیج کامل (ZIP)", zip_path),
        _download_entry("گزارش PDF", pdf_path),
        _download_entry("داده JSON", json_path),
    ]
    for key, path in excel_paths.items():
        files.append(_download_entry(EXCEL_LABELS.get(key, path.name), path))

    _append_report_index(
        project_slug,
        {
            "report_id": report_id,
            "site_url": result.get("site_url"),
            "sitemap_url": result.get("sitemap_url"),
            "generated_at": result.get("generated_at"),
            "score": result.get("score"),
            "pages_checked": result.get("pages_checked"),
            "issue_count": len(result.get("issues") or []),
            "severity_counts": result.get("severity_counts") or {},
        },
    )

    result_out = dict(result)
    result_out.update(
        {
            "project_slug": project_slug,
            "report_id": report_id,
            "files": files,
            "pdf_path": _relative_to_root(pdf_path),
            "package_path": _relative_to_root(zip_path),
        }
    )
    if on_progress:
        on_progress(100, "گزارش آماده شد")
    return result_out


def find_report_json(project_slug: str, report_id: str) -> Path:
    """Resolve JSON path for a report_id; raise FileNotFoundError if missing."""
    path = audit_output_dir(project_slug) / f"{report_id}.json"
    if not path.is_file():
        raise FileNotFoundError(f"Report not found: {report_id}")
    return path


def recheck_from_excel(
    project_slug: str,
    excel_path: Path,
    *,
    report_id: str = "",
    concurrency: int = 6,
    timeout: int = 20,
    on_progress: Optional[Callable[[int, str], None]] = None,
) -> Dict[str, Any]:
    """
    Re-audit open Excel rows and notify which issues are still present.

    Input:
        project_slug: Project scope.
        excel_path: Uploaded tracking workbook.
        report_id: Optional override; else read from Excel «شناسه گزارش».

    Output:
        Summary: marked_done, still_open, resolved, notifications, details.
    """
    parsed_report_id, rows = parse_status_workbook(excel_path)
    rid = (report_id or parsed_report_id or "").strip()
    if not rid:
        raise ValueError(
            "شناسه گزارش در اکسل یافت نشد — از فایل خروجی همین ابزار استفاده کنید."
        )

    json_path = find_report_json(project_slug, rid)
    original = json.loads(json_path.read_text(encoding="utf-8"))
    site_url = str(original.get("site_url") or "")
    sitemap_url = str(original.get("sitemap_url") or "")

    done_count = sum(1 for r in rows if r.get("is_done"))
    open_pairs = open_issue_pairs(rows)
    if on_progress:
        on_progress(5, f"خواندن اکسل — {len(open_pairs)} مورد باز")

    if not open_pairs:
        return {
            "report_id": rid,
            "project_slug": project_slug,
            "marked_done": done_count,
            "open_submitted": 0,
            "still_open": 0,
            "resolved": 0,
            "notification": (
                "همه ردیف‌های اکسل به‌عنوان انجام‌شده علامت خورده‌اند — "
                "مورد بازی برای بررسی مجدد نیست."
            ),
            "level": "success",
            "still_open_items": [],
            "resolved_items": [],
        }

    page_urls: List[str] = []
    for issue_id, url in open_pairs:
        if not issue_id.startswith("site_") and url:
            page_urls.append(url)
    seen_u: Set[str] = set()
    unique_pages: List[str] = []
    for u in page_urls:
        if u not in seen_u:
            seen_u.add(u)
            unique_pages.append(u)

    if on_progress:
        on_progress(15, f"بررسی مجدد {len(unique_pages)} صفحه…")

    auditor = TechnicalSeoAuditor(
        site_url or "https://example.com",
        unique_pages,
        max_pages=max(len(unique_pages), 1) if unique_pages else 1,
        timeout=max(5, timeout),
        concurrency=max(1, min(concurrency, 12)),
        link_check_limit=min(40, max(10, len(unique_pages) or 10)),
        configured_sitemap_url=sitemap_url,
    )
    fresh = auditor.run(on_progress=on_progress)

    fresh_map: Dict[str, Set[str]] = {}
    for issue in fresh.get("issues") or []:
        iid = str(issue.get("issue_id") or "")
        urls = set(issue.get("urls") or issue.get("sample_urls") or [])
        if not urls and iid.startswith("site_"):
            urls = {site_url}
        fresh_map[iid] = {u.rstrip("/") for u in urls}

    still_open: List[Dict[str, str]] = []
    resolved: List[Dict[str, str]] = []
    for issue_id, url in open_pairs:
        norm = (url or site_url).rstrip("/")
        present_urls = fresh_map.get(issue_id) or set()
        if issue_id.startswith("site_"):
            still = issue_id in fresh_map
        else:
            still = norm in present_urls or url in present_urls
        item: Dict[str, str] = {"issue_id": issue_id, "url": url}
        for r in rows:
            if r.get("issue_id") == issue_id and (not url or r.get("url") == url):
                item["title"] = str(r.get("title") or "")
                break
        if still:
            still_open.append(item)
        else:
            resolved.append(item)

    still_n = len(still_open)
    resolved_n = len(resolved)
    if still_n == 0:
        level = "success"
        notification = (
            f"عالی — از {len(open_pairs)} مورد باز، همه در بررسی مجدد پاس شدند "
            f"({resolved_n} مورد حل‌شده). {done_count} ردیف از قبل تیک خورده بود."
        )
    elif resolved_n == 0:
        level = "warning"
        notification = (
            f"توجه — هر {still_n} مورد باز هنوز در سایت وجود دارد. "
            f"لطفاً اصلاحات را کامل کنید و دوباره آپلود کنید."
        )
    else:
        level = "info"
        notification = (
            f"{resolved_n} مورد برطرف شده؛ {still_n} مورد هنوز باز است. "
            f"جزئیات موارد باقی‌مانده در نتیجه آمده است."
        )

    out_dir = audit_output_dir(project_slug)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_path = out_dir / f"{rid}_recheck_{stamp}.json"
    payload = {
        "report_id": rid,
        "project_slug": project_slug,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "marked_done": done_count,
        "open_submitted": len(open_pairs),
        "still_open": still_n,
        "resolved": resolved_n,
        "notification": notification,
        "level": level,
        "still_open_items": still_open,
        "resolved_items": resolved,
        "source_excel": excel_path.name,
    }
    log_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    payload["log"] = _download_entry("لاگ بررسی مجدد", log_path)
    return payload
