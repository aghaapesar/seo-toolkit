"""Unit tests for ProjectManager."""

import pytest

from src.services.project_manager import ProjectManager


def test_create_and_list_projects(tmp_path):
    """Projects should be stored in registry with isolated folders."""
    mgr = ProjectManager(base_dir=str(tmp_path / "projects"))
    p1 = mgr.create_project("Site A", "site-a.com", "https://site-a.com/sitemap.xml")
    p2 = mgr.create_project("Site B", "site-b.com")

    projects = mgr.list_projects()
    assert len(projects) == 2
    assert {p.slug for p in projects} == {p1.slug, p2.slug}

    paths = mgr.get_paths(p1.slug)
    paths.ensure()
    assert paths.input_dir.exists()
    assert paths.output_dir.exists()


def test_duplicate_slug_raises(tmp_path):
    """Creating two projects with same slug should fail."""
    mgr = ProjectManager(base_dir=str(tmp_path / "projects"))
    mgr.create_project("My Site", "example.com", slug="my-site")
    with pytest.raises(ValueError):
        mgr.create_project("Other", "other.com", slug="my-site")


def test_resolve_by_domain(tmp_path):
    """resolve_project should match domain."""
    mgr = ProjectManager(base_dir=str(tmp_path / "projects"))
    created = mgr.create_project("Shop", "shop.example.com")
    found = mgr.resolve_project(domain="shop.example.com")
    assert found is not None
    assert found.slug == created.slug
