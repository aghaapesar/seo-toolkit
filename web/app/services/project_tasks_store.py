"""
Project task Kanban persistence (SQLite).

Input:
    project_slug, task title/notes/status/priority/tags/due_date/assignee, subtasks.

Output:
    Per-project task board for reminder Kanban UI.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from web.app.services.auth_service import get_user_by_id, list_project_members
from web.app.services.database import get_connection

TASK_STATUSES = ("pending", "in_progress", "done")
TASK_PRIORITIES = ("low", "medium", "high")

PRIORITY_LABELS = {
    "low": ("Low", "کم"),
    "medium": ("Medium", "متوسط"),
    "high": ("High", "بالا"),
}


def _utc_now() -> str:
    """ISO timestamp in UTC."""
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    """Generate short unique id."""
    return uuid.uuid4().hex[:12]


def normalize_task_status(status: Optional[str]) -> str:
    """Map unknown status to a valid column key."""
    if status in TASK_STATUSES:
        return status
    legacy = {
        "planned": "pending",
        "writing": "in_progress",
        "review": "in_progress",
        "published": "done",
    }
    return legacy.get(status or "", "pending")


def normalize_priority(priority: Optional[str]) -> str:
    """Map unknown priority to low/medium/high."""
    p = (priority or "medium").strip().lower()
    if p in TASK_PRIORITIES:
        return p
    return "medium"


def normalize_tags(tags: Optional[str]) -> str:
    """
    Normalize comma-separated tags to lowercase unique list.

    Input:
        tags: Raw tag string e.g. "SEO, Blog, seo".

    Output:
        Comma-separated unique tags.
    """
    if not tags:
        return ""
    parts = [t.strip().lower() for t in re.split(r"[,،;|]", tags) if t.strip()]
    seen: set[str] = set()
    unique: List[str] = []
    for tag in parts:
        if tag not in seen:
            seen.add(tag)
            unique.append(tag)
    return ", ".join(unique)


def normalize_due_date(due_date: Optional[str]) -> str:
    """
    Validate due date as YYYY-MM-DD or empty.

    Output:
        Normalized date string or empty.
    """
    raw = (due_date or "").strip()
    if not raw:
        return ""
    if re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        return raw
    raise ValueError("due_date must be YYYY-MM-DD")


def normalize_assignee_id(value: Optional[int]) -> Optional[int]:
    """Map 0/None to unassigned."""
    if value is None or value == 0:
        return None
    return int(value)


def tags_to_list(tags: str) -> List[str]:
    """Split stored tags string to list."""
    if not tags:
        return []
    return [t.strip() for t in tags.split(",") if t.strip()]


def _assignee_payload(user_id: Optional[int]) -> Optional[Dict[str, Any]]:
    """Resolve assignee user id to display dict."""
    uid = normalize_assignee_id(user_id)
    if not uid:
        return None
    user = get_user_by_id(uid)
    if not user:
        return None
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name or user.username,
    }


def validate_assignee_for_project(project_slug: str, user_id: Optional[int]) -> Optional[int]:
    """
    Ensure assignee belongs to project members.

    Output:
        Normalized user id or None.
    """
    uid = normalize_assignee_id(user_id)
    if not uid:
        return None
    member_ids = {m["id"] for m in list_project_members(project_slug)}
    if uid not in member_ids and member_ids:
        raise ValueError("Assignee must be a project member")
    return uid


def _parse_subtask_row(row: Any) -> Dict[str, Any]:
    """Deserialize one subtask row."""
    item = dict(row)
    item["done"] = bool(item.get("done"))
    item["assignee"] = _assignee_payload(item.get("assigned_user_id"))
    return item


def _parse_row(row: Any, *, subtasks: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Deserialize one task row."""
    item = dict(row)
    item["status"] = normalize_task_status(item.get("status"))
    item["priority"] = normalize_priority(item.get("priority"))
    item["tags"] = item.get("tags") or ""
    item["tags_list"] = tags_to_list(item["tags"])
    item["due_date"] = item.get("due_date") or ""
    item["assignee"] = _assignee_payload(item.get("assigned_user_id"))
    item["subtasks"] = subtasks if subtasks is not None else list_subtasks(item["id"])
    done_count = sum(1 for s in item["subtasks"] if s.get("done"))
    item["subtask_done"] = done_count
    item["subtask_total"] = len(item["subtasks"])
    return item


def list_subtasks(task_id: str) -> List[Dict[str, Any]]:
    """List subtasks for a task ordered by sort_order."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT * FROM project_task_subtasks
        WHERE task_id = ?
        ORDER BY sort_order ASC, created_at ASC
        """,
        (task_id,),
    ).fetchall()
    return [_parse_subtask_row(r) for r in rows]


def list_tasks(project_slug: str) -> List[Dict[str, Any]]:
    """
    List all tasks for a project ordered by column, priority, then sort_order.

    Output:
        Task dicts sorted for Kanban display.
    """
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT * FROM project_tasks
        WHERE project_slug = ?
        ORDER BY
          CASE status
            WHEN 'pending' THEN 0
            WHEN 'in_progress' THEN 1
            WHEN 'done' THEN 2
            ELSE 3
          END,
          CASE priority
            WHEN 'high' THEN 0
            WHEN 'medium' THEN 1
            WHEN 'low' THEN 2
            ELSE 3
          END,
          CASE WHEN due_date != '' THEN due_date ELSE '9999-12-31' END ASC,
          sort_order ASC,
          created_at ASC
        """,
        (project_slug,),
    ).fetchall()
    return [_parse_row(r) for r in rows]


def get_board(project_slug: str) -> Dict[str, Any]:
    """
    Load Kanban board payload for one project.

    Output:
        Dict with project_slug, items, members, and counts.
    """
    items = list_tasks(project_slug)
    members = list_project_members(project_slug)
    return {
        "project_slug": project_slug,
        "items": items,
        "members": members,
        "priorities": list(TASK_PRIORITIES),
        "counts": {
            "pending": sum(1 for i in items if i["status"] == "pending"),
            "in_progress": sum(1 for i in items if i["status"] == "in_progress"),
            "done": sum(1 for i in items if i["status"] == "done"),
            "total": len(items),
        },
    }


def create_task(
    project_slug: str,
    title: str,
    *,
    notes: str = "",
    status: str = "pending",
    priority: str = "medium",
    tags: str = "",
    due_date: str = "",
    assigned_user_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Create a new project task card.

    Input:
        project_slug: Owning project.
        title: Task title (required).

    Output:
        Created task dict.
    """
    title = (title or "").strip()
    if not title:
        raise ValueError("Task title is required")

    assignee = validate_assignee_for_project(project_slug, assigned_user_id)

    conn = get_connection()
    max_order = conn.execute(
        """
        SELECT COALESCE(MAX(sort_order), -1) AS m FROM project_tasks
        WHERE project_slug = ? AND status = ?
        """,
        (project_slug, normalize_task_status(status)),
    ).fetchone()["m"]

    task_id = _new_id()
    now = _utc_now()
    conn.execute(
        """
        INSERT INTO project_tasks (
            id, project_slug, title, notes, status, priority, tags, due_date,
            assigned_user_id, sort_order, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            task_id,
            project_slug,
            title,
            (notes or "").strip(),
            normalize_task_status(status),
            normalize_priority(priority),
            normalize_tags(tags),
            normalize_due_date(due_date),
            assignee,
            int(max_order) + 1,
            now,
            now,
        ),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM project_tasks WHERE id = ?", (task_id,)).fetchone()
    return _parse_row(row)


def update_task(
    task_id: str,
    *,
    title: Optional[str] = None,
    notes: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    tags: Optional[str] = None,
    due_date: Optional[str] = None,
    assigned_user_id: Optional[int] = ...,  # type: ignore
) -> Dict[str, Any]:
    """
    Update task fields.

    Output:
        Updated task dict.
    """
    conn = get_connection()
    row = conn.execute("SELECT * FROM project_tasks WHERE id = ?", (task_id,)).fetchone()
    if not row:
        raise ValueError("Task not found")

    fields: List[str] = []
    values: List[Any] = []

    if title is not None:
        t = title.strip()
        if not t:
            raise ValueError("Task title cannot be empty")
        fields.append("title = ?")
        values.append(t)
    if notes is not None:
        fields.append("notes = ?")
        values.append(notes.strip())
    if status is not None:
        fields.append("status = ?")
        values.append(normalize_task_status(status))
    if priority is not None:
        fields.append("priority = ?")
        values.append(normalize_priority(priority))
    if tags is not None:
        fields.append("tags = ?")
        values.append(normalize_tags(tags))
    if due_date is not None:
        fields.append("due_date = ?")
        values.append(normalize_due_date(due_date))
    if assigned_user_id is not ...:
        assignee = validate_assignee_for_project(row["project_slug"], assigned_user_id)
        fields.append("assigned_user_id = ?")
        values.append(assignee)

    if not fields:
        return _parse_row(row)

    fields.append("updated_at = ?")
    values.append(_utc_now())
    values.append(task_id)

    conn.execute(f"UPDATE project_tasks SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    updated = conn.execute("SELECT * FROM project_tasks WHERE id = ?", (task_id,)).fetchone()
    return _parse_row(updated)


def delete_task(task_id: str) -> None:
    """Permanently delete a task and its subtasks."""
    conn = get_connection()
    conn.execute("DELETE FROM project_tasks WHERE id = ?", (task_id,))
    conn.commit()


def get_task_project_slug(task_id: str) -> Optional[str]:
    """Return project_slug for access checks."""
    conn = get_connection()
    row = conn.execute(
        "SELECT project_slug FROM project_tasks WHERE id = ?",
        (task_id,),
    ).fetchone()
    return row["project_slug"] if row else None


def create_subtask(
    task_id: str,
    title: str,
    *,
    assigned_user_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Add a subtask under a parent task.

    Output:
        Created subtask dict.
    """
    title = (title or "").strip()
    if not title:
        raise ValueError("Subtask title is required")

    conn = get_connection()
    parent = conn.execute(
        "SELECT project_slug FROM project_tasks WHERE id = ?",
        (task_id,),
    ).fetchone()
    if not parent:
        raise ValueError("Task not found")

    assignee = validate_assignee_for_project(parent["project_slug"], assigned_user_id)
    max_order = conn.execute(
        "SELECT COALESCE(MAX(sort_order), -1) AS m FROM project_task_subtasks WHERE task_id = ?",
        (task_id,),
    ).fetchone()["m"]

    sub_id = _new_id()
    now = _utc_now()
    conn.execute(
        """
        INSERT INTO project_task_subtasks (
            id, task_id, title, done, assigned_user_id, sort_order, created_at
        ) VALUES (?, ?, ?, 0, ?, ?, ?)
        """,
        (sub_id, task_id, title, assignee, int(max_order) + 1, now),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM project_task_subtasks WHERE id = ?", (sub_id,)).fetchone()
    return _parse_subtask_row(row)


def update_subtask(
    subtask_id: str,
    *,
    title: Optional[str] = None,
    done: Optional[bool] = None,
    assigned_user_id: Optional[int] = ...,
) -> Dict[str, Any]:  # type: ignore
    """Update subtask fields."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM project_task_subtasks WHERE id = ?", (subtask_id,)).fetchone()
    if not row:
        raise ValueError("Subtask not found")

    parent = conn.execute(
        "SELECT project_slug FROM project_tasks WHERE id = ?",
        (row["task_id"],),
    ).fetchone()
    if not parent:
        raise ValueError("Parent task not found")

    fields: List[str] = []
    values: List[Any] = []

    if title is not None:
        t = title.strip()
        if not t:
            raise ValueError("Subtask title cannot be empty")
        fields.append("title = ?")
        values.append(t)
    if done is not None:
        fields.append("done = ?")
        values.append(1 if done else 0)
    if assigned_user_id is not ...:
        assignee = validate_assignee_for_project(parent["project_slug"], assigned_user_id)
        fields.append("assigned_user_id = ?")
        values.append(assignee)

    if not fields:
        return _parse_subtask_row(row)

    values.append(subtask_id)
    conn.execute(f"UPDATE project_task_subtasks SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    updated = conn.execute("SELECT * FROM project_task_subtasks WHERE id = ?", (subtask_id,)).fetchone()
    return _parse_subtask_row(updated)


def delete_subtask(subtask_id: str) -> None:
    """Delete one subtask."""
    conn = get_connection()
    conn.execute("DELETE FROM project_task_subtasks WHERE id = ?", (subtask_id,))
    conn.commit()


def get_subtask_parent_task_id(subtask_id: str) -> Optional[str]:
    """Return parent task id for access checks."""
    conn = get_connection()
    row = conn.execute(
        "SELECT task_id FROM project_task_subtasks WHERE id = ?",
        (subtask_id,),
    ).fetchone()
    return row["task_id"] if row else None
