"""HTML page routes for Seo Toolkit UI."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from web.app.i18n import get_lang, page_context, t

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(tags=["pages"])

TOOL_PAGES = {
    "content": ("tools/content.html", "Content Analysis", "تحلیل محتوا"),
    "scraping": ("tools/scraping.html", "SEO Scraping", "اسکرپ سئو"),
    "generation": ("tools/generation.html", "Content Generation", "تولید محتوا"),
    "linking": ("tools/linking.html", "Internal Linking", "لینک‌سازی داخلی"),
    "synonyms": ("tools/synonyms.html", "Synonym Finder", "مترادف‌یاب"),
    "index-diff": ("tools/index_diff.html", "URL Index Diff", "تفکیک ایندکس"),
}


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    """Main dashboard with all tools."""
    lang = request.query_params.get("lang") or request.cookies.get("lang", "fa")
    title = t(lang, "nav_dashboard")
    return TEMPLATES.TemplateResponse(
        request, "dashboard.html", page_context(request, title, tool_id=None)
    )


@router.get("/tools/{tool_id}", response_class=HTMLResponse)
def tool_page(request: Request, tool_id: str):
    """Render individual tool page."""
    if tool_id not in TOOL_PAGES:
        return TEMPLATES.TemplateResponse(
            request,
            "errors/404.html",
            page_context(request, "404"),
            status_code=404,
        )
    template, title_en, title_fa = TOOL_PAGES[tool_id]
    lang = request.query_params.get("lang") or request.cookies.get("lang", "fa")
    title = title_fa if lang == "fa" else title_en
    return TEMPLATES.TemplateResponse(
        request, template, page_context(request, title, tool_id=tool_id)
    )


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    """Settings and config status."""
    lang = request.query_params.get("lang") or request.cookies.get("lang", "fa")
    title = t(lang, "nav_settings")
    return TEMPLATES.TemplateResponse(
        request, "settings.html", page_context(request, title, tool_id=None)
    )


@router.get("/projects", response_class=HTMLResponse)
def projects_page(request: Request):
    """Project management page."""
    lang = get_lang(request)
    title = t(lang, "nav_projects")
    return TEMPLATES.TemplateResponse(
        request, "projects.html", page_context(request, title, tool_id=None)
    )


@router.get("/tasks/{job_id}", response_class=HTMLResponse)
def task_progress_page(request: Request, job_id: str):
    """Background task progress page with live status."""
    lang = get_lang(request)
    title = t(lang, "task_progress_title")
    return TEMPLATES.TemplateResponse(
        request,
        "tasks/progress.html",
        page_context(request, title, tool_id="index-diff", job_id=job_id),
    )
