"""Tests for read-only dashboard summary."""

import pytest

from web.app.services import database
from web.app.services.calendar_store import create_board_from_calendar_rows, create_campaign
from web.app.services.dashboard_service import get_dashboard_summary
from web.app.services.project_tasks_store import create_task


@pytest.fixture
def temp_db(monkeypatch, tmp_path):
    path = tmp_path / "test.db"
    monkeypatch.setattr(database, "DB_PATH", path)
    database.reset_init_flag()
    yield path


def test_dashboard_summary_without_project(temp_db):
    """Global summary works without project scope."""
    data = get_dashboard_summary()
    assert data["has_project"] is False
    assert "recent_jobs" in data
    assert data["tasks"]["total"] == 0


def test_dashboard_summary_with_project_counts(temp_db):
    """Per-project KPIs aggregate tasks and calendar items."""
    create_task("shop", "Fix meta tags", status="pending")
    create_task("shop", "Blog outline", status="in_progress")
    camp = create_campaign("shop", "کمپین ۱")
    rows = [{"publish_date": "2026-08-01", "suggested_title": "Post A", "status": "pending"}]
    create_board_from_calendar_rows(rows, project_slug="shop", campaign_id=camp["id"])

    data = get_dashboard_summary(project_slug="shop")
    assert data["has_project"] is True
    assert data["tasks"]["total"] == 2
    assert data["calendar"]["items_total"] == 1
    assert data["calendar"]["campaigns"] == 1
