"""Health check router."""

from fastapi import APIRouter

from src import __version__

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    """Return service health and version."""
    return {"status": "ok", "name": "Seo Toolkit", "version": __version__}
