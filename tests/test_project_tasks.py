"""Tests for per-project task Kanban store."""

import pytest

from web.app.services import database
from web.app.services.auth_service import create_user, grant_project_access
from web.app.services.project_tasks_store import (
    create_subtask,
    create_task,
    delete_task,
    list_tasks,
    normalize_due_date,
    normalize_tags,
    update_subtask,
    update_task,
)


@pytest.fixture
def temp_db(monkeypatch, tmp_path):
    path = tmp_path / "test.db"
    monkeypatch.setattr(database, "DB_PATH", path)
    database.reset_init_flag()
    yield path


def test_project_tasks_crud_isolated_by_project(temp_db):
    """Tasks are scoped per project_slug."""
    create_task("alpha", "Fix sitemap", notes="Check robots.txt", priority="high", tags="seo, tech")
    create_task("alpha", "Blog audit", due_date="2026-08-01")
    create_task("beta", "Beta only task")

    alpha = list_tasks("alpha")
    beta = list_tasks("beta")
    assert len(alpha) == 2
    assert len(beta) == 1
    assert alpha[0]["priority"] == "high"
    assert "seo" in alpha[0]["tags_list"]

    task_id = alpha[1]["id"]
    updated = update_task(task_id, status="in_progress", tags="blog, content")
    assert updated["status"] == "in_progress"
    assert "blog" in updated["tags_list"]

    delete_task(task_id)
    assert len(list_tasks("alpha")) == 1


def test_normalize_tags_and_due_date():
    """Tags dedupe; due date validates format."""
    assert normalize_tags("SEO, blog, SEO") == "seo, blog"
    assert normalize_due_date("2026-12-31") == "2026-12-31"
    assert normalize_due_date("") == ""
    with pytest.raises(ValueError):
        normalize_due_date("31-12-2026")


def test_assignee_and_subtasks(temp_db):
    """Assignee must be project member; subtasks nest under parent."""
    user = create_user("tasker", "pass1234", display_name="Task Owner")
    grant_project_access(user.id, "alpha")

    parent = create_task("alpha", "Main task", assigned_user_id=user.id)
    assert parent["assignee"]["id"] == user.id

    sub = create_subtask(parent["id"], "Sub item one", assigned_user_id=user.id)
    assert sub["title"] == "Sub item one"
    assert sub["assignee"]["id"] == user.id

    done = update_subtask(sub["id"], done=True)
    assert done["done"] is True

    tasks = list_tasks("alpha")
    assert tasks[0]["subtask_total"] == 1
    assert tasks[0]["subtask_done"] == 1

    with pytest.raises(ValueError):
        create_task("alpha", "Bad assignee", assigned_user_id=99999)
