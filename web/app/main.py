"""FastAPI application for Seo Toolkit."""

from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src import __version__
from web.app.routers import health, index_diff

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(
    title="Seo Toolkit API",
    description="Persian SEO toolkit - index diff, content analysis, and automation",
    version=__version__,
)

static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

app.include_router(health.router)
app.include_router(index_diff.router)


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    """Render main dashboard."""
    return TEMPLATES.TemplateResponse(
        request,
        "dashboard.html",
        {"title": "Seo Toolkit", "version": __version__},
    )


@app.get("/index-diff", response_class=HTMLResponse)
def index_diff_page(request: Request):
    """Render index diff form page."""
    return TEMPLATES.TemplateResponse(
        request,
        "index_diff.html",
        {"title": "URL Index Diff", "version": __version__},
    )


@app.post("/index-diff", response_class=HTMLResponse)
async def index_diff_submit(
    request: Request,
    domain: str = Form(...),
    sitemap_url: str = Form(...),
    mark_submitted: bool = Form(False),
):
    """Handle index diff form submission via API logic."""
    result = index_diff.run_diff(
        index_diff.DiffRequest(
            domain=domain,
            sitemap_url=sitemap_url,
            mark_submitted=mark_submitted,
        )
    )
    return TEMPLATES.TemplateResponse(
        request,
        "index_diff_result.html",
        {"title": "Diff Result", "result": result},
    )
