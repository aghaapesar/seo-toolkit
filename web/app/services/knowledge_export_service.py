"""
Knowledge export web service — project-scoped RAG Markdown export.

Input:
    project_slug, sitemap URL, export options.

Output:
    Export summary dict with downloadable file entries and registry state.
"""

from __future__ import annotations

import json
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from src.ai_model_manager import AIModelManager
from src.knowledge_exporter.config import KnowledgeExporterConfig
from src.knowledge_exporter.exporter import KnowledgeExporter
from src.knowledge_exporter.sitemap_lastmod import fetch_url_lastmod_map
from src.services.project_manager import ProjectManager
from web.app.services.file_download import _relative_to_root, resolve_download_path
from web.app.services.knowledge_export_store import (
    compute_staleness_report,
    list_pages,
    mark_downloaded_by_path,
)


def export_output_dir(project_slug: str) -> Path:
    """
    Resolve knowledge export output directory for a project.

    Output:
        Path to projects/{slug}/output/knowledge_export/
    """
    paths = ProjectManager().get_paths(project_slug)
    return paths.output_dir / "knowledge_export"


def _file_entry(label: str, path: Path, *, page_type: str = "", status: str = "") -> Dict[str, str]:
    """Build downloadable file descriptor for UI."""
    rel = _relative_to_root(path)
    entry: Dict[str, str] = {
        "label": label,
        "name": path.name,
        "path": rel,
        "download_url": f"/api/v1/knowledge-export/download?path={rel}",
    }
    if page_type:
        entry["page_type"] = page_type
    if status:
        entry["status"] = status
    return entry


def list_export_files(output_dir: Path, project_slug: str = "") -> List[Dict[str, str]]:
    """
    List per-URL pages, part files, and index.json in export directory.

    Output:
        Sorted list of file_entry dicts with optional registry status.
    """
    if not output_dir.is_dir():
        return []

    registry_by_path: Dict[str, Dict[str, Any]] = {}
    if project_slug:
        for row in list_pages(project_slug):
            rel = row.get("relative_path") or ""
            if rel:
                registry_by_path[rel] = row

    entries: List[Dict[str, str]] = []
    index_path = output_dir / "index.json"
    if index_path.is_file():
        entries.append(_file_entry("index.json", index_path))

    pages_dir = output_dir / "pages"
    if pages_dir.is_dir():
        for md in sorted(pages_dir.rglob("*.md")):
            rel_in_output = md.relative_to(output_dir).as_posix()
            reg = registry_by_path.get(rel_in_output, {})
            label = md.relative_to(pages_dir).as_posix()
            entries.append(
                _file_entry(
                    label,
                    md,
                    page_type=reg.get("page_type") or md.parent.name,
                    status=reg.get("status") or "exported",
                )
            )

    for part in sorted(output_dir.glob("knowledge_part_*.md")):
        entries.append(_file_entry(part.name, part))
    return entries


def analysis_cache_dir(project_slug: str) -> Path:
    """Directory for saved sitemap analysis JSON files."""
    return export_output_dir(project_slug) / ".analysis"


def build_url_type_map(analysis: Dict[str, Any], selected_segment_ids: List[str]) -> Dict[str, str]:
    """
    Map each URL to content_type from selected analysis segments.

    Output:
        URL → page_type dict.
    """
    segments = {s["id"]: s for s in analysis.get("segments") or []}
    segment_urls: Dict[str, List[str]] = analysis.get("segment_urls") or {}
    url_types: Dict[str, str] = {}
    for seg_id in selected_segment_ids:
        seg = segments.get(seg_id, {})
        ct = seg.get("content_type") or "other"
        for page_url in segment_urls.get(seg_id, []):
            url_types.setdefault(page_url, ct)
    return url_types


def test_export_model(model_name: str) -> Dict[str, Any]:
    """
    Test AI model connection before export job.

    Output:
        Dict with connected flag and error message.
    """
    manager = AIModelManager()
    model = manager.get_model(model_name.strip() or None) or manager.get_default_model()
    if not model:
        return {"connected": False, "error": "No AI model configured", "name": model_name}
    ok = model.test_connection()
    return {
        "name": getattr(model, "name", model_name),
        "connected": ok,
        "error": getattr(model, "error_message", "") or "",
    }


def analyze_project_sitemap(
    project_slug: str,
    *,
    sitemap_url: str = "",
    timeout: int = 45,
    max_retries: int = 3,
) -> Dict[str, Any]:
    """
    Analyze sitemap for a project and cache result for segment selection.

    Output:
        Analysis summary with optional staleness report.
    """
    manager = ProjectManager()
    project = manager.get_project(project_slug)
    if not project:
        raise ValueError(f"Project not found: {project_slug}")

    resolved = (sitemap_url or project.sitemap_url or "").strip()
    if not resolved:
        raise ValueError("Sitemap URL is required (set on project or in form)")

    from src.knowledge_exporter.sitemap_analyzer import analyze_sitemap, save_analysis

    full = analyze_sitemap(resolved, timeout=timeout, max_retries=max_retries)
    save_analysis(analysis_cache_dir(project_slug), full)

    lastmod_map = fetch_url_lastmod_map(resolved, timeout=timeout, max_retries=max_retries)
    staleness = compute_staleness_report(project_slug, lastmod_map)

    return {
        "analysis_id": full["analysis_id"],
        "project_slug": project_slug,
        "sitemap_url": full["sitemap_url"],
        "generated_at": full["generated_at"],
        "total_urls": full["total_urls"],
        "pattern_count": full.get("pattern_count", len(full.get("segments") or [])),
        "sitemap_sources": full.get("sitemap_sources") or [],
        "segments": full["segments"],
        "warnings": full.get("warnings") or [],
        "staleness": staleness,
    }


def get_analysis(project_slug: str, analysis_id: str) -> Optional[Dict[str, Any]]:
    """Load cached analysis for export."""
    from src.knowledge_exporter.sitemap_analyzer import load_analysis

    return load_analysis(analysis_cache_dir(project_slug), analysis_id)


def resolve_export_urls(
    project_slug: str,
    analysis_id: str,
    selected_segment_ids: List[str],
) -> List[str]:
    """
    Resolve URL list from cached analysis and selected segments.

    Output:
        Deduped URLs to scrape.
    """
    from src.knowledge_exporter.sitemap_analyzer import resolve_selected_urls

    analysis = get_analysis(project_slug, analysis_id)
    if not analysis:
        raise ValueError("Sitemap analysis expired — run Analyze again")
    return resolve_selected_urls(analysis, selected_segment_ids)


def get_dashboard(project_slug: str) -> Dict[str, Any]:
    """
    Summary for knowledge export tool UI.

    Output:
        Latest export metadata, registry rows, and downloadable files.
    """
    out_dir = export_output_dir(project_slug)
    index_path = out_dir / "index.json"
    latest: Optional[Dict[str, Any]] = None
    if index_path.is_file():
        try:
            latest = json.loads(index_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            latest = None

    registry = list_pages(project_slug, limit=2000)
    return {
        "output_dir": _relative_to_root(out_dir) if out_dir.exists() else "",
        "latest": latest,
        "files": list_export_files(out_dir, project_slug),
        "registry": registry,
        "registry_count": len(registry),
    }


def run_knowledge_export(
    project_slug: str,
    *,
    sitemap_url: str = "",
    urls: Optional[List[str]] = None,
    analysis_id: str = "",
    selected_segment_ids: Optional[List[str]] = None,
    model_name: str = "",
    use_llm: bool = True,
    include_blog: bool = False,
    include_noindex: bool = False,
    product_sample_limit: int = 0,
    write_parts: bool = True,
    skip_unchanged: bool = True,
    max_part_kb: int = 500,
    max_pages_per_part: int = 50,
    include_pattern: Optional[str] = None,
    exclude_pattern: Optional[str] = None,
    concurrency: int = 4,
    rate_limit_seconds: float = 0.25,
    timeout: int = 45,
    max_retries: int = 3,
    min_content_chars: int = 100,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
) -> Dict[str, Any]:
    """
    Run full RAG knowledge export for a project.

    Input:
        project_slug: Active project.
        model_name: AI model for LLM structuring (required when use_llm=True).
        on_progress: Optional (processed, total, message) callback.

    Output:
        Result dict for job.result with stats and files list.
    """
    manager = ProjectManager()
    project = manager.get_project(project_slug)
    if not project:
        raise ValueError(f"Project not found: {project_slug}")

    resolved_sitemap = (sitemap_url or project.sitemap_url or "").strip()

    export_urls: List[str] = []
    url_page_types: Dict[str, str] = {}
    if urls:
        export_urls = list(urls)
    elif analysis_id:
        seg_ids = selected_segment_ids or []
        if not seg_ids:
            raise ValueError("Select at least one content segment")
        analysis = get_analysis(project_slug, analysis_id)
        if not analysis:
            raise ValueError("Sitemap analysis expired — run Analyze again")
        export_urls = resolve_export_urls(project_slug, analysis_id, seg_ids)
        url_page_types = build_url_type_map(analysis, seg_ids)
    elif resolved_sitemap:
        pass
    else:
        raise ValueError("Sitemap URL is required (set on project or in form)")

    llm_model = None
    if use_llm:
        ai = AIModelManager()
        llm_model = ai.get_model(model_name.strip() or None) or ai.get_default_model()
        if not llm_model:
            raise ValueError("AI model required for LLM export — configure in Settings")
        if not llm_model.test_connection():
            raise ValueError(
                llm_model.error_message or "AI model connection test failed — check Settings"
            )

    lastmod_map: Dict[str, str] = {}
    if resolved_sitemap:
        lastmod_map = fetch_url_lastmod_map(
            resolved_sitemap,
            timeout=max(10, timeout),
            max_retries=max_retries,
        )

    out_dir = export_output_dir(project_slug)
    out_dir.mkdir(parents=True, exist_ok=True)

    config = KnowledgeExporterConfig(
        output_dir=out_dir,
        sitemap_url=resolved_sitemap if not export_urls else "",
        urls=export_urls,
        max_part_bytes=max(64, max_part_kb) * 1024,
        max_pages_per_part=max(1, min(max_pages_per_part, 200)),
        include_pattern=include_pattern or None,
        exclude_pattern=exclude_pattern or None,
        concurrency=max(1, min(concurrency, 16)),
        rate_limit_seconds=max(0.0, rate_limit_seconds),
        timeout=max(10, timeout),
        max_retries=max(1, max_retries),
        min_content_chars=max(0, min_content_chars),
        cache_dir=out_dir / ".cache",
        use_llm=use_llm,
        model_name=model_name,
        include_blog=include_blog,
        include_noindex=include_noindex,
        product_sample_limit=max(0, product_sample_limit),
        write_parts=write_parts,
        skip_unchanged=skip_unchanged,
        url_page_types=url_page_types or None,
        lastmod_map=lastmod_map or None,
        project_slug=project_slug,
    )

    exporter = KnowledgeExporter(config, llm_model=llm_model)
    summary = exporter.run(on_progress=on_progress, use_tqdm=False)

    if summary.total_urls == 0 and summary.warnings:
        raise ValueError(summary.warnings[0])

    files = list_export_files(out_dir, project_slug)
    result = summary.to_dict()
    result.update(
        {
            "project_slug": project_slug,
            "sitemap_url": resolved_sitemap,
            "analysis_id": analysis_id or "",
            "selected_segments": selected_segment_ids or [],
            "model_name": model_name,
            "files": files,
            "index_path": _relative_to_root(out_dir / "index.json")
            if (out_dir / "index.json").is_file()
            else "",
        }
    )
    return result


def resolve_export_download(relative_path: str, *, project_slug: str = "") -> Path:
    """
    Validate and resolve a knowledge export file for download.

    Output:
        Absolute file path.

    Raises:
        ValueError: Invalid or missing path.
    """
    path = resolve_download_path(relative_path)
    if project_slug and "/pages/" in relative_path.replace("\\", "/"):
        mark_downloaded_by_path(project_slug, relative_path)
    return path


def build_zip_archive(project_slug: str, relative_paths: List[str]) -> BytesIO:
    """
    Build ZIP of selected export files preserving folder structure.

    Input:
        project_slug: For download tracking.
        relative_paths: Repo-relative file paths.

    Output:
        BytesIO ZIP buffer positioned at start.
    """
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in relative_paths:
            rel = rel.strip()
            if not rel:
                continue
            path = resolve_download_path(rel)
            arcname = rel.split("knowledge_export/", 1)[-1] if "knowledge_export/" in rel else path.name
            zf.write(path, arcname=arcname)
            if project_slug and "/pages/" in rel.replace("\\", "/"):
                mark_downloaded_by_path(project_slug, rel)
    buffer.seek(0)
    return buffer
