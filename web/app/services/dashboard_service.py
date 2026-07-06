"""
Read-only dashboard aggregates for the web home page.

Input:
    Optional project_slug and authenticated user context.

Output:
    KPI counts, chart series, and recent background jobs — no mutations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.services.project_manager import ProjectManager
from web.app.services.auth_service import user_can_access_project
from web.app.services.calendar_store import KANBAN_STATUSES, list_campaigns
from web.app.services.database import get_connection
from web.app.services.job_manager import job_manager
from web.app.services.product_gap_store import get_latest_snapshot
from web.app.services.site_index_store import get_index_stats


def _empty_counts(keys: tuple[str, ...]) -> Dict[str, int]:
    """Build zero-filled counter dict for known status keys."""
    return {k: 0 for k in keys}


def _task_counts(project_slug: str) -> Dict[str, int]:
    """Count project tasks per Kanban column."""
    counts = _empty_counts(("pending", "in_progress", "done"))
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT status, COUNT(*) AS c FROM project_tasks
        WHERE project_slug = ?
        GROUP BY status
        """,
        (project_slug,),
    ).fetchall()
    for row in rows:
        key = row["status"] or "pending"
        if key in counts:
            counts[key] = int(row["c"])
    return counts


def _calendar_counts(project_slug: str) -> Dict[str, int]:
    """Count content calendar items per Kanban column for a project."""
    counts = _empty_counts(KANBAN_STATUSES)
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT i.status, COUNT(*) AS c
        FROM calendar_items i
        JOIN calendar_boards b ON b.id = i.board_id
        WHERE b.project_slug = ?
        GROUP BY i.status
        """,
        (project_slug,),
    ).fetchall()
    for row in rows:
        key = row["status"] or "pending"
        if key in counts:
            counts[key] = int(row["c"])
    return counts


def _recent_jobs(limit: int = 8) -> List[Dict[str, Any]]:
    """Return latest background jobs (newest first)."""
    jobs = job_manager.list_recent(limit)
    out: List[Dict[str, Any]] = []
    for job in jobs:
        entry = job.to_dict()
        entry["progress_url"] = f"/tasks/{job.id}"
        out.append(entry)
    return out


def get_dashboard_summary(
    *,
    project_slug: Optional[str] = None,
    user_id: Optional[int] = None,
    is_admin: bool = False,
) -> Dict[str, Any]:
    """
    Build dashboard payload for charts and KPI cards.

    Output:
        Summary dict safe for JSON API (read-only).
    """
    manager = ProjectManager()
    projects = manager.list_projects()
    slug = (project_slug or "").strip()

    summary: Dict[str, Any] = {
        "project_slug": slug,
        "projects_count": len(projects),
        "has_project": bool(slug),
        "config_ok": True,
        "site_index": {"total_pages": 0, "by_type": {}},
        "product_gap": {"has_snapshot": False, "on_site_count": 0, "missing_count": 0, "analyzed_at": ""},
        "calendar": {"campaigns": 0, "items_total": 0, "by_status": _empty_counts(KANBAN_STATUSES)},
        "tasks": {"total": 0, "by_status": _empty_counts(("pending", "in_progress", "done"))},
        "recent_jobs": _recent_jobs(8),
    }

    if not slug:
        return summary

    if user_id is not None and not user_can_access_project(user_id, slug, is_admin=is_admin):
        summary["access_denied"] = True
        return summary

    index_stats = get_index_stats(slug)
    summary["site_index"] = {
        "total_pages": index_stats.get("total_pages") or 0,
        "by_type": index_stats.get("by_type") or {},
        "latest_run_status": (index_stats.get("latest_run") or {}).get("status", ""),
    }

    gap = get_latest_snapshot(slug)
    if gap:
        summary["product_gap"] = {
            "has_snapshot": True,
            "on_site_count": int(gap.get("on_site_count") or 0),
            "missing_count": int(gap.get("missing_count") or 0),
            "analyzed_at": gap.get("analyzed_at") or "",
        }

    campaigns = list_campaigns(slug)
    cal_by_status = _calendar_counts(slug)
    summary["calendar"] = {
        "campaigns": len(campaigns),
        "items_total": sum(cal_by_status.values()),
        "by_status": cal_by_status,
    }

    task_by_status = _task_counts(slug)
    summary["tasks"] = {
        "total": sum(task_by_status.values()),
        "by_status": task_by_status,
    }

    return summary
