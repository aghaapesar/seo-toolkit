"""Project tasks Kanban API — per-project reminder board."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from web.app.deps.auth import require_user
from web.app.services.auth_service import User, list_project_members, user_can_access_project
from web.app.services.project_tasks_store import (
    TASK_PRIORITIES,
    TASK_STATUSES,
    create_subtask,
    create_task,
    delete_subtask,
    delete_task,
    get_board,
    get_subtask_parent_task_id,
    get_task_project_slug,
    update_subtask,
    update_task,
)

router = APIRouter(prefix="/api/v1/project-tasks", tags=["project-tasks"])


class TaskCreateRequest(BaseModel):
    """POST body for a new task."""

    project_slug: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    notes: str = ""
    priority: str = "medium"
    tags: str = ""
    due_date: str = ""
    assigned_user_id: Optional[int] = None


class TaskUpdateRequest(BaseModel):
    """PATCH body for task card."""

    title: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    tags: Optional[str] = None
    due_date: Optional[str] = None
    assigned_user_id: Optional[int] = None


class SubtaskCreateRequest(BaseModel):
    """POST body for a new subtask."""

    title: str = Field(..., min_length=1)
    assigned_user_id: Optional[int] = None


class SubtaskUpdateRequest(BaseModel):
    """PATCH body for subtask."""

    title: Optional[str] = None
    done: Optional[bool] = None
    assigned_user_id: Optional[int] = None


def _assert_access(user: User, project_slug: str) -> None:
    if not user_can_access_project(user.id, project_slug, is_admin=user.is_admin):
        raise HTTPException(status_code=403, detail="No access to this project")


def _assert_task_access(user: User, task_id: str) -> str:
    slug = get_task_project_slug(task_id)
    if not slug:
        raise HTTPException(status_code=404, detail="Task not found")
    _assert_access(user, slug)
    return slug


def _assert_subtask_access(user: User, subtask_id: str) -> str:
    task_id = get_subtask_parent_task_id(subtask_id)
    if not task_id:
        raise HTTPException(status_code=404, detail="Subtask not found")
    return _assert_task_access(user, task_id)


def _validate_priority(priority: Optional[str]) -> None:
    if priority and priority not in TASK_PRIORITIES:
        raise HTTPException(status_code=400, detail="Invalid priority")


def _members_payload(project_slug: str, user: User) -> list:
    """Members for assignee dropdown; fallback to current user."""
    members = list_project_members(project_slug)
    if not members:
        members = [
            {
                "id": user.id,
                "username": user.username,
                "display_name": user.display_name or user.username,
                "role": "editor",
            }
        ]
    return members


@router.get("/statuses")
def task_statuses():
    """Return valid Kanban column keys and priorities."""
    return {"statuses": list(TASK_STATUSES), "priorities": list(TASK_PRIORITIES)}


@router.get("/members")
def task_members(project_slug: str, user: User = Depends(require_user)):
    """List project members available for task assignment."""
    slug = project_slug.strip()
    if not slug:
        raise HTTPException(status_code=400, detail="project_slug required")
    _assert_access(user, slug)
    return {"members": _members_payload(slug, user)}


@router.get("/board")
def task_board(project_slug: str, user: User = Depends(require_user)):
    """Load all tasks for a project Kanban board."""
    slug = project_slug.strip()
    if not slug:
        raise HTTPException(status_code=400, detail="project_slug required")
    _assert_access(user, slug)
    board = get_board(slug)
    if not board.get("members"):
        board["members"] = _members_payload(slug, user)
    return board


@router.post("/tasks")
def task_create(payload: TaskCreateRequest, user: User = Depends(require_user)):
    """Add a new task card to the project board."""
    slug = payload.project_slug.strip()
    _assert_access(user, slug)
    _validate_priority(payload.priority)
    try:
        task = create_task(
            slug,
            payload.title,
            notes=payload.notes,
            priority=payload.priority,
            tags=payload.tags,
            due_date=payload.due_date,
            assigned_user_id=payload.assigned_user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"task": task}


@router.patch("/tasks/{task_id}")
def task_update(task_id: str, payload: TaskUpdateRequest, user: User = Depends(require_user)):
    """Update task fields including assignee and due date."""
    _assert_task_access(user, task_id)
    if payload.status and payload.status not in TASK_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    _validate_priority(payload.priority)
    try:
        task = update_task(
            task_id,
            title=payload.title,
            notes=payload.notes,
            status=payload.status,
            priority=payload.priority,
            tags=payload.tags,
            due_date=payload.due_date,
            assigned_user_id=payload.assigned_user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"task": task}


@router.delete("/tasks/{task_id}")
def task_delete(task_id: str, user: User = Depends(require_user)):
    """Delete a task card."""
    _assert_task_access(user, task_id)
    delete_task(task_id)
    return {"ok": True}


@router.post("/tasks/{task_id}/subtasks")
def subtask_create(task_id: str, payload: SubtaskCreateRequest, user: User = Depends(require_user)):
    """Add a subtask to a task card."""
    _assert_task_access(user, task_id)
    try:
        subtask = create_subtask(
            task_id,
            payload.title,
            assigned_user_id=payload.assigned_user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"subtask": subtask}


@router.patch("/subtasks/{subtask_id}")
def subtask_update(subtask_id: str, payload: SubtaskUpdateRequest, user: User = Depends(require_user)):
    """Update subtask title, done state, or assignee."""
    _assert_subtask_access(user, subtask_id)
    try:
        subtask = update_subtask(
            subtask_id,
            title=payload.title,
            done=payload.done,
            assigned_user_id=payload.assigned_user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"subtask": subtask}


@router.delete("/subtasks/{subtask_id}")
def subtask_delete(subtask_id: str, user: User = Depends(require_user)):
    """Delete a subtask."""
    _assert_subtask_access(user, subtask_id)
    delete_subtask(subtask_id)
    return {"ok": True}
