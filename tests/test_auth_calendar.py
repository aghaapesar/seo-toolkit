"""Tests for auth password hashing and calendar store."""

import os
import tempfile
from pathlib import Path

import pytest

from web.app.services import database
from web.app.services.auth_service import authenticate, create_user, hash_password, verify_password
from web.app.services.calendar_store import (
    create_board_from_calendar_rows,
    create_campaign,
    delete_campaign,
    delete_item,
    get_board,
    get_campaign_board,
    list_campaigns,
    update_item,
)


@pytest.fixture
def temp_db(monkeypatch):
    """Use isolated SQLite file per test."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.db"
        monkeypatch.setattr(database, "DB_PATH", path)
        monkeypatch.setattr(database, "_initialized", False)
        database.reset_init_flag()
        yield path


def test_password_hash_roundtrip():
    """Hash and verify password."""
    stored = hash_password("secret123")
    assert verify_password("secret123", stored)
    assert not verify_password("wrong", stored)


def test_create_and_authenticate_user(temp_db):
    """User registration and login."""
    user = create_user("editor1", "pass1234", display_name="Editor")
    assert user.username == "editor1"
    authed = authenticate("editor1", "pass1234")
    assert authed and authed.id == user.id


def test_calendar_board_kanban_update(temp_db):
    """Create board and update item status."""
    rows = [
        {
            "publish_date": "2026-07-10",
            "suggested_title": "Test article",
            "h2_headings": ["H2 one", "H2 two"],
            "keywords": ["kw1", "kw2"],
            "difficulty_label": "آسان",
            "status": "pending",
        }
    ]
    board = create_board_from_calendar_rows(rows, title="Test board")
    assert board["items"][0]["status"] == "pending"
    item_id = board["items"][0]["id"]
    updated = update_item(item_id, status="in_progress", notes="در حال کار")
    assert updated["status"] == "in_progress"
    assert updated["notes"] == "در حال کار"
    loaded = get_board(board["id"])
    assert len(loaded["items"]) == 1
    assert loaded["items"][0]["checklist"]


def test_campaigns_per_project(temp_db):
    """Campaigns group calendar items per project."""
    camp = create_campaign("site-a", "کمپین ۱")
    rows = [
        {
            "publish_date": "2026-07-10",
            "suggested_title": "Article A",
            "h2_headings": ["H1"],
            "keywords": ["kw"],
            "status": "planned",
        }
    ]
    board = create_board_from_calendar_rows(rows, project_slug="site-a", campaign_id=camp["id"], title="Board A")
    assert board["campaign_id"] == camp["id"]
    campaigns = list_campaigns("site-a")
    assert len(campaigns) == 1
    assert campaigns[0]["item_count"] == 1
    view = get_campaign_board(camp["id"])
    assert len(view["items"]) == 1
    item_id = view["items"][0]["id"]
    camp2 = create_campaign("site-a", "کمپین ۲")
    moved = update_item(item_id, campaign_id=camp2["id"])
    assert moved["campaign_id"] == camp2["id"]
    assert len(get_campaign_board(camp["id"])["items"]) == 0
    assert len(get_campaign_board(camp2["id"])["items"]) == 1


def test_calendar_assignee(temp_db):
    """Assign calendar card to a project member."""
    from web.app.services.auth_service import grant_project_access

    user = create_user("writer1", "pass1234", display_name="Writer")
    grant_project_access(user.id, "site-c")
    camp = create_campaign("site-c", "کمپین نویسنده")
    rows = [{"publish_date": "2026-09-01", "suggested_title": "Post", "status": "pending"}]
    board = create_board_from_calendar_rows(rows, project_slug="site-c", campaign_id=camp["id"])
    item_id = board["items"][0]["id"]
    updated = update_item(item_id, assigned_user_id=user.id)
    assert updated["assignee"]["id"] == user.id
    loaded = get_campaign_board(camp["id"])
    assert loaded["items"][0]["assignee"]["username"] == "writer1"


def test_delete_item_and_campaign(temp_db):
    """Delete single item or entire campaign."""
    camp = create_campaign("site-b", "کمپین حذف")
    rows = [
        {"publish_date": "2026-08-01", "suggested_title": "A", "status": "planned"},
        {"publish_date": "2026-08-02", "suggested_title": "B", "status": "planned"},
    ]
    board = create_board_from_calendar_rows(rows, project_slug="site-b", campaign_id=camp["id"])
    item_ids = [i["id"] for i in board["items"]]
    assert delete_item(item_ids[0])
    assert len(get_campaign_board(camp["id"])["items"]) == 1
    assert delete_campaign(camp["id"])
    assert get_campaign_board(camp["id"]) is None
    assert len(list_campaigns("site-b")) == 0
