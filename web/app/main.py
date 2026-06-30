"""FastAPI application for Seo Toolkit."""

import logging
import traceback
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src import __version__
from web.app.routers import health, index_diff, modes, pages

logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Seo Toolkit API",
    description="Persian SEO toolkit — full UI and REST API",
    version=__version__,
)


@app.exception_handler(Exception)
async def unhandled_exception(request: Request, exc: Exception):
    """Log and return readable errors instead of blank 500 pages."""
    logger.error("Unhandled error on %s: %s", request.url.path, exc, exc_info=True)
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=500, content={"detail": str(exc)})
    return HTMLResponse(
        status_code=500,
        content=f"<pre style='padding:2rem;font-family:monospace'>500 Error\n\n{exc}\n\nRestart with:\n  ./scripts/run_web.sh</pre>",
    )


static_dir = BASE_DIR / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

app.include_router(health.router)
app.include_router(index_diff.router)
app.include_router(modes.router)
app.include_router(pages.router)
