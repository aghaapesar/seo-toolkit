"""HTML page routes for Seo Toolkit UI."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from urllib.parse import quote

from web.app.deps.auth import get_optional_user
from web.app.i18n import get_lang, page_context, t
from web.app.services.calendar_store import get_board, get_board_by_job
from web.app.services.job_manager import job_manager
from web.app.tool_registry import JOB_TYPE_TO_TOOL, tool_requires_login

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(tags=["pages"])

# Display titles: (template, title_en, title_fa) — keep in sync with TOOLS in i18n.py
TOOL_PAGES = {
    "content": ("tools/content.html", "Content Analysis", "تحلیل محتوا"),
    "scraping": ("tools/scraping.html", "Metadata Export", "استخراج متادیتا"),
    "generation": ("tools/generation.html", "Content Generation", "تولید محتوا"),
    "linking": ("tools/linking.html", "Link Inserter", "درج لینک در محتوا"),
    "synonyms": ("tools/synonyms.html", "Synonym Finder", "مترادف‌یاب"),
    "index-diff": ("tools/index_diff.html", "URL Index Diff", "تفکیک ایندکس"),
    "content-cluster": ("tools/content_cluster.html", "Content Cluster", "کلاستر محتوا"),
    "content-audit": ("tools/content_audit.html", "Calendar Sync", "تطبیق تقویم محتوا"),
    "site-index": ("tools/site_index.html", "Site Index", "ایندکس سایت"),
    "product-gap": ("tools/product_gap.html", "Product Gap", "شکاف محصولات"),
    "internal-links": ("tools/internal_links.html", "Internal Link Hub", "هاب لینک داخلی"),
    "knowledge-export": ("tools/knowledge_export.html", "Knowledge Base Export", "خروجی Knowledge Base"),
    "project-tasks": ("tools/project_tasks.html", "Project Tasks", "یادداشت تسک‌ها"),
    "service-status": ("tools/service_status.html", "Service Status", "وضعیت سرویس‌ها"),
    "technical-audit": ("tools/technical_audit.html", "Technical Issues Check", "بررسی مشکلات فنی"),
}


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    """Main dashboard with all tools."""
    lang = request.query_params.get("lang") or request.cookies.get("lang", "fa")
    title = t(lang, "nav_dashboard")
    return TEMPLATES.TemplateResponse(
        request, "dashboard.html", page_context(request, title, tool_id=None)
    )


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    """Username/password login page."""
    lang = get_lang(request)
    title = t(lang, "login_title")
    return TEMPLATES.TemplateResponse(
        request,
        "login.html",
        page_context(request, title, tool_id=None),
    )


@router.get("/tools/content-cluster/calendar", response_class=HTMLResponse)
def calendar_kanban_page(request: Request):
    """Kanban board for content calendar (requires login)."""
    lang = get_lang(request)
    user = get_optional_user(request)
    if not user:
        next_path = request.url.path
        if request.url.query:
            next_path += f"?{request.url.query}"
        return RedirectResponse(url=f"/login?lang={lang}&next={quote(next_path)}")

    board_id = request.query_params.get("board_id", "")
    job_id = request.query_params.get("job_id", "")
    board_download = ""
    if board_id:
        board = get_board(board_id)
    elif job_id:
        board = get_board_by_job(job_id)
    else:
        board = None

    if board and board.get("job_id"):
        job = job_manager.get(board["job_id"])
        if job and job.result and job.result.get("output_file"):
            board_download = f"/api/v1/content-cluster/download?path={quote(job.result['output_file'])}"

    title = t(lang, "calendar_kanban_title")
    ctx = page_context(request, title, tool_id="content-cluster")
    ctx["board_download"] = board_download
    return TEMPLATES.TemplateResponse(request, "tools/calendar_kanban.html", ctx)


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
    lang = request.query_params.get("lang") or request.cookies.get("lang", "fa")

    # Single source of truth: web.app.tool_registry.LOGIN_REQUIRED_TOOLS
    if tool_requires_login(tool_id):
        user = get_optional_user(request)
        if not user:
            next_path = request.url.path
            if request.url.query:
                next_path += f"?{request.url.query}"
            return RedirectResponse(url=f"/login?lang={lang}&next={quote(next_path)}")

    template, title_en, title_fa = TOOL_PAGES[tool_id]
    title = title_fa if lang == "fa" else title_en
    ctx = page_context(request, title, tool_id=tool_id)

    if tool_id == "product-gap":
        from web.app.services.auth_service import user_can_access_project
        from web.app.services.product_gap_store import get_latest_snapshot, list_uploads

        user = get_optional_user(request)
        active_slug = ctx.get("active_project_slug") or ""
        gap_bootstrap: dict | None = None
        if user and active_slug and user_can_access_project(
            user.id, active_slug, is_admin=user.is_admin
        ):
            uploads = list_uploads(active_slug)
            snap = get_latest_snapshot(active_slug)
            gap_bootstrap = {
                "has_snapshot": bool(snap),
                "upload_count": len(uploads),
                "on_site_count": (snap or {}).get("on_site_count", 0),
                "missing_count": (snap or {}).get("missing_count", 0),
                "analyzed_at": (snap or {}).get("analyzed_at", ""),
                "use_ai_match": ((snap or {}).get("analysis") or {}).get("use_ai_match", False),
            }
        ctx["gap_bootstrap"] = gap_bootstrap

    return TEMPLATES.TemplateResponse(request, template, ctx)


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
    job = job_manager.get(job_id)
    job_type = job.job_type if job else ""
    tool_id = JOB_TYPE_TO_TOOL.get(job_type, "index-diff")
    tool_route = f"/tools/{tool_id}"
    back_label_key = f"back_to_tool_{tool_id.replace('-', '_')}"
    back_label = t(lang, back_label_key)
    ctx = page_context(request, title, tool_id=tool_id, job_id=job_id)
    ctx.update(
        {
            "job_type": job_type,
            "tool_route": tool_route,
            "back_to_tool_label": back_label,
        }
    )
    return TEMPLATES.TemplateResponse(request, "tasks/progress.html", ctx)
