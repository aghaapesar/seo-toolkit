"""FastAPI application for Seo Toolkit."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src import __version__
from web.app.routers import health, index_diff, modes, pages

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Seo Toolkit API",
    description="Persian SEO toolkit — full UI and REST API",
    version=__version__,
)

static_dir = BASE_DIR / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

app.include_router(health.router)
app.include_router(index_diff.router)
app.include_router(modes.router)
app.include_router(pages.router)
