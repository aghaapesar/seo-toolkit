"""
Project Manager — multi-project registry with isolated data directories.

Each project gets its own input, output, knowledge_base, index_history, and sitemap cache.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class Project:
    """Single Seo Toolkit project definition."""

    slug: str
    name: str
    domain: str
    sitemap_url: str = ""
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        """Serialize project to JSON-safe dict."""
        return asdict(self)


@dataclass
class ProjectPaths:
    """Filesystem paths scoped to one project."""

    root: Path
    input_dir: Path
    output_dir: Path
    knowledge_base_dir: Path
    index_history_dir: Path
    sitemaps_dir: Path

    def ensure(self) -> None:
        """Create all project directories if missing."""
        for path in (
            self.root,
            self.input_dir,
            self.output_dir,
            self.knowledge_base_dir,
            self.index_history_dir,
            self.sitemaps_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)


class ProjectManager:
    """
    CRUD for projects and path resolution.

    Registry file: projects/registry.json
    Project data: projects/{slug}/
    """

    REGISTRY_FILE = "registry.json"

    def __init__(self, base_dir: str = "projects") -> None:
        """
        Initialize project manager.

        Input:
            base_dir: Root folder for all projects.
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.registry_path = self.base_dir / self.REGISTRY_FILE
        self._projects: Dict[str, Project] = {}
        self._load()

    @staticmethod
    def slugify(name: str) -> str:
        """
        Convert display name to filesystem-safe slug.

        Input:
            name: Human-readable project name.

        Output:
            Lowercase slug with hyphens.
        """
        slug = re.sub(r"[^\w\s-]", "", name.strip().lower())
        slug = re.sub(r"[-\s]+", "-", slug).strip("-")
        return slug or f"project-{uuid.uuid4().hex[:6]}"

    def _load(self) -> None:
        """Load project registry from disk."""
        if not self.registry_path.exists():
            self._projects = {}
            return
        with open(self.registry_path, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
        self._projects = {
            item["slug"]: Project(**item) for item in raw.get("projects", [])
        }

    def _save(self) -> None:
        """Persist registry to disk."""
        payload = {
            "updated_at": datetime.now().isoformat(),
            "projects": [p.to_dict() for p in self._projects.values()],
        }
        with open(self.registry_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

    def list_projects(self) -> List[Project]:
        """Return all projects sorted by name."""
        return sorted(self._projects.values(), key=lambda p: p.name.lower())

    def get_project(self, slug: str) -> Optional[Project]:
        """Get project by slug or None."""
        return self._projects.get(slug)

    def create_project(
        self,
        name: str,
        domain: str,
        sitemap_url: str = "",
        notes: str = "",
        slug: Optional[str] = None,
    ) -> Project:
        """
        Create a new project with isolated directories.

        Input:
            name: Display name.
            domain: Primary domain (e.g. example.com).
            sitemap_url: Default sitemap URL for tools.
            notes: Optional description.
            slug: Optional custom slug; auto-generated if omitted.

        Output:
            Created Project instance.

        Raises:
            ValueError: If slug already exists or fields invalid.
        """
        if len(name.strip()) < 2:
            raise ValueError("Project name must be at least 2 characters")
        if len(domain.strip()) < 3:
            raise ValueError("Domain must be at least 3 characters")

        final_slug = slug or self.slugify(name)
        if final_slug in self._projects:
            raise ValueError(f"Project slug already exists: {final_slug}")

        project = Project(
            slug=final_slug,
            name=name.strip(),
            domain=domain.strip(),
            sitemap_url=sitemap_url.strip(),
            notes=notes.strip(),
        )
        self._projects[final_slug] = project
        self.get_paths(final_slug).ensure()
        self._save()
        return project

    def update_project(
        self,
        slug: str,
        name: Optional[str] = None,
        domain: Optional[str] = None,
        sitemap_url: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Project:
        """Update project fields and save registry."""
        project = self._projects.get(slug)
        if not project:
            raise ValueError(f"Project not found: {slug}")

        if name is not None:
            project.name = name.strip()
        if domain is not None:
            project.domain = domain.strip()
        if sitemap_url is not None:
            project.sitemap_url = sitemap_url.strip()
        if notes is not None:
            project.notes = notes.strip()
        project.updated_at = datetime.now().isoformat()
        self._save()
        return project

    def delete_project(self, slug: str) -> None:
        """
        Remove project from registry (data folders remain on disk).

        Input:
            slug: Project identifier.
        """
        if slug not in self._projects:
            raise ValueError(f"Project not found: {slug}")
        del self._projects[slug]
        self._save()

    def get_paths(self, slug: str) -> ProjectPaths:
        """
        Resolve isolated paths for a project.

        Input:
            slug: Project identifier.

        Output:
            ProjectPaths with root and subfolder paths.
        """
        root = self.base_dir / slug
        return ProjectPaths(
            root=root,
            input_dir=root / "input",
            output_dir=root / "output",
            knowledge_base_dir=root / "knowledge_base",
            index_history_dir=root / "index_history",
            sitemaps_dir=root / "sitemaps",
        )

    def resolve_project(
        self, slug: Optional[str] = None, domain: Optional[str] = None
    ) -> Optional[Project]:
        """
        Find project by slug or domain.

        Input:
            slug: Project slug.
            domain: Fallback domain match.

        Output:
            Matching Project or None.
        """
        if slug and slug in self._projects:
            return self._projects[slug]
        if domain:
            domain_l = domain.strip().lower()
            for project in self._projects.values():
                if project.domain.lower() == domain_l or project.slug == self.slugify(domain):
                    return project
        return None
