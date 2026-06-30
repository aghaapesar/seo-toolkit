"""Project management API."""

from typing import List, Optional

from fastapi import APIRouter, Form, HTTPException
from pydantic import BaseModel, Field

from src.services.project_manager import ProjectManager

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])

_manager = ProjectManager()


class ProjectCreate(BaseModel):
    """Create project request body."""

    name: str = Field(..., min_length=2)
    domain: str = Field(..., min_length=3)
    sitemap_url: str = ""
    notes: str = ""


class ProjectOut(BaseModel):
    """Project response."""

    slug: str
    name: str
    domain: str
    sitemap_url: str
    notes: str
    created_at: str
    updated_at: str


@router.get("", response_model=List[ProjectOut])
def list_projects():
    """List all registered projects."""
    return [ProjectOut(**p.to_dict()) for p in _manager.list_projects()]


@router.get("/{slug}", response_model=ProjectOut)
def get_project(slug: str):
    """Get one project by slug."""
    project = _manager.get_project(slug)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectOut(**project.to_dict())


@router.post("", response_model=ProjectOut)
def create_project(payload: ProjectCreate):
    """Create a new isolated project."""
    try:
        project = _manager.create_project(
            name=payload.name,
            domain=payload.domain,
            sitemap_url=payload.sitemap_url,
            notes=payload.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ProjectOut(**project.to_dict())


@router.post("/form", response_model=ProjectOut)
def create_project_form(
    name: str = Form(...),
    domain: str = Form(...),
    sitemap_url: str = Form(""),
    notes: str = Form(""),
):
    """Create project from HTML form."""
    try:
        project = _manager.create_project(name, domain, sitemap_url, notes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ProjectOut(**project.to_dict())


def get_manager() -> ProjectManager:
    """Return shared project manager instance."""
    return _manager


def resolve_project_paths(slug: Optional[str]):
    """Get project and paths or raise 404."""
    if not slug:
        return None, None
    project = _manager.get_project(slug)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project not found: {slug}")
    paths = _manager.get_paths(slug)
    paths.ensure()
    return project, paths
