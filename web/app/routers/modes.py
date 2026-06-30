"""REST API for all Seo Toolkit operational modes."""

import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from src.ai_model_manager import AIModelManager
from src.internal_linker import InternalLinker
from src.page_scraper import PageScraper
from src.services.url_index_tracker import UrlIndexTracker
from src.synonym_finder import SynonymFinder
from web.app.routers import index_diff
from web.app.routers.projects import resolve_project_paths
from web.app.services.sitemap_fetch import fetch_all_sitemap_urls

router = APIRouter(prefix="/api/v1", tags=["modes"])

UPLOAD_DIR = Path("output/web_uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _load_config() -> dict:
    """Load config.yaml from project root."""
    config_path = Path("config.yaml")
    if not config_path.exists():
        raise HTTPException(
            status_code=503,
            detail="config.yaml not found. Copy config.sample.yaml to config.yaml.",
        )
    with open(config_path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _save_upload(upload: UploadFile, prefix: str) -> Path:
    """Persist uploaded file and return path."""
    suffix = Path(upload.filename or "file").suffix or ".bin"
    dest = UPLOAD_DIR / f"{prefix}_{uuid.uuid4().hex[:8]}{suffix}"
    with open(dest, "wb") as out:
        shutil.copyfileobj(upload.file, out)
    return dest


class ScrapingResponse(BaseModel):
    """SEO scraping job result."""

    output_file: str
    url_count: int
    test_mode: bool


class LinkingResponse(BaseModel):
    """Internal linking result."""

    output_file: str
    sitemap_url_count: int


class SynonymsResponse(BaseModel):
    """Synonym finder result."""

    output_file: str
    model: str


@router.post("/scraping", response_model=ScrapingResponse)
def run_scraping(
    sitemap_url: str = Form(...),
    test_mode: bool = Form(False),
    project_slug: str = Form(""),
):
    """
    Scrape SEO metadata for all sitemap URLs.

    Input: sitemap URL, optional test_mode (10 pages).
    Output: path to Excel audit file.
    """
    urls = fetch_all_sitemap_urls(sitemap_url)
    if not urls:
        raise HTTPException(status_code=404, detail="No URLs found in sitemap")

    if test_mode:
        urls = urls[:10]

    scraper = PageScraper()
    if project_slug:
        _, paths = resolve_project_paths(project_slug)
        scraper = PageScraper(output_dir=str(paths.output_dir))
    output_file = scraper.scrape_urls_batch(
        urls=urls, sitemap_url=sitemap_url, test_mode=test_mode, non_interactive=True
    )
    return ScrapingResponse(
        output_file=str(output_file),
        url_count=len(urls),
        test_mode=test_mode,
    )


@router.post("/linking", response_model=LinkingResponse)
async def run_linking(
    sitemap_url: str = Form(...),
    html_file: UploadFile = File(...),
    project_slug: str = Form(""),
):
    """
    Add internal links to uploaded HTML using sitemap URLs.

    Input: sitemap URL + HTML file upload.
    Output: linked HTML file path.
    """
    urls = fetch_all_sitemap_urls(sitemap_url)
    if not urls:
        raise HTTPException(status_code=404, detail="No URLs in sitemap")

    saved = _save_upload(html_file, "linking")
    content = saved.read_text(encoding="utf-8")
    linker = InternalLinker(urls)
    linked = linker.add_internal_links(content)

    if project_slug:
        _, paths = resolve_project_paths(project_slug)
        out = paths.output_dir / f"{saved.stem}_linked.html"
    else:
        out = saved.parent / f"{saved.stem}_linked.html"
    out.write_text(linked, encoding="utf-8")

    return LinkingResponse(output_file=str(out), sitemap_url_count=len(urls))


@router.post("/synonyms", response_model=SynonymsResponse)
async def run_synonyms(
    excel_file: UploadFile = File(...),
    project_slug: str = Form(""),
):
    """
    Find keyword synonyms from uploaded Excel (column 1).

    Input: Excel file with keywords.
    Output: Excel with variation columns.
    """
    config = _load_config()
    manager = AIModelManager()
    manager.test_all_connections()
    model = manager.get_default_model() or (
        manager.get_connected_models()[0] if manager.get_connected_models() else None
    )
    if not model:
        raise HTTPException(
            status_code=503,
            detail="No connected AI model. Configure API keys in config.yaml.",
        )

    saved = _save_upload(excel_file, "synonyms")
    if project_slug:
        _, paths = resolve_project_paths(project_slug)
        output_dir = str(paths.output_dir / "synonyms")
    else:
        output_dir = "output/synonyms"
    finder = SynonymFinder(config)
    output = finder.process_excel_file(
        excel_path=str(saved),
        ai_model=model,
        output_dir=output_dir,
    )
    return SynonymsResponse(output_file=str(output), model=model.name)


class ContentJobRequest(BaseModel):
    """Content analysis request (file must be uploaded separately)."""

    project_name: str = Field(..., min_length=3)
    sitemap_url: str
    test_mode: bool = True
    file_id: str


@router.post("/content/upload")
async def content_upload(
    project_name: str = Form(...),
    sitemap_url: str = Form(...),
    test_mode: bool = Form(True),
    excel_file: UploadFile = File(...),
    project_slug: str = Form(""),
):
    """
    Save Search Console Excel and return CLI command for full AI analysis.

    Input: project, sitemap, Excel upload.
    Output: saved path and recommended CLI command.
    """
    saved = _save_upload(excel_file, "content")
    if project_slug:
        _, paths = resolve_project_paths(project_slug)
        dest = paths.input_dir / saved.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(saved, dest)
        project_flag = f" --project {project_slug}"
    else:
        dest = Path("input") / saved.name
        dest.parent.mkdir(exist_ok=True)
        shutil.copy(saved, dest)
        project_flag = ""
    flag = " --test" if test_mode else ""
    return {
        "message": "File saved to input/. Run CLI for full AI analysis.",
        "saved_path": str(dest),
        "cli": f"python main.py --mode content{flag}{project_flag}",
        "project_name": project_name,
        "sitemap_url": sitemap_url,
    }


@router.post("/generation/upload")
async def generation_upload(
    project_name: str = Form(...),
    excel_file: UploadFile = File(None),
    project_slug: str = Form(""),
):
    """Save generation Excel and return CLI instructions."""
    path_msg = ""
    project_flag = f" --project {project_slug}" if project_slug else ""
    if excel_file and excel_file.filename:
        saved = _save_upload(excel_file, "generation")
        if project_slug:
            _, paths = resolve_project_paths(project_slug)
            out = paths.output_dir / saved.name
        else:
            out = Path("output") / saved.name
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(saved, out)
        path_msg = str(out)
    return {
        "message": "Use CLI for interactive AI generation with model selection.",
        "saved_path": path_msg,
        "cli": f"python main.py --mode generation{project_flag}",
        "project_name": project_name,
    }


@router.post("/content")
def run_content_info():
    """
    Content mode requires CLI for full AI workflow.

    Returns guidance for CLI usage; use upload endpoint in future iteration.
    """
    return {
        "message": "Full content analysis uses interactive AI steps.",
        "cli": "python main.py --mode content --test",
        "docs": "docs/ARCHITECTURE.md",
    }


@router.post("/generation")
def run_generation_info():
    """Content generation info endpoint."""
    return {
        "message": "Run after content mode produces Excel in output/.",
        "cli": "python main.py --mode generation",
    }


@router.get("/index-diff/status/{domain}")
def index_diff_status(domain: str):
    """Proxy to index diff status."""
    return index_diff.get_status(domain)


@router.post("/index-diff/diff", response_model=index_diff.DiffResponse)
def index_diff_run(payload: index_diff.DiffRequest):
    """Proxy to index diff run."""
    return index_diff.run_diff(payload)
