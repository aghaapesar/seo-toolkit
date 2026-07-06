"""
Content calendar Kanban persistence (SQLite).

Input:
    Cluster job results or calendar JSON rows.

Output:
    Board + item records for Kanban UI, grouped by per-project campaigns.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from web.app.services.auth_service import get_user_by_id
from web.app.services.database import get_connection
from web.app.services.project_tasks_store import (
    normalize_assignee_id,
    validate_assignee_for_project,
)

# Kanban column statuses (3-column workflow).
KANBAN_STATUSES = ("pending", "in_progress", "done")

# Legacy 5-column values mapped on read/write for older clients.
LEGACY_STATUS_MAP = {
    "planned": "pending",
    "writing": "in_progress",
    "review": "in_progress",
    "scheduled": "in_progress",
    "published": "done",
}


def normalize_kanban_status(status: Optional[str]) -> str:
    """Map legacy or unknown status to a valid Kanban column."""
    if not status:
        return "pending"
    normalized = LEGACY_STATUS_MAP.get(status, status)
    if normalized not in KANBAN_STATUSES:
        return "pending"
    return normalized

DEFAULT_CHECKLIST = [
    {"id": "research", "label_fa": "تحقیق کیورد", "label_en": "Keyword research", "done": False},
    {"id": "outline", "label_fa": "طرح outline", "label_en": "Outline ready", "done": False},
    {"id": "draft", "label_fa": "پیش‌نویس", "label_en": "First draft", "done": False},
    {"id": "h2", "label_fa": "H2ها درج شد", "label_en": "H2 sections added", "done": False},
    {"id": "meta", "label_fa": "متا و عنوان سئو", "label_en": "SEO meta/title", "done": False},
    {"id": "images", "label_fa": "تصاویر", "label_en": "Images", "done": False},
    {"id": "internal_links", "label_fa": "لینک داخلی", "label_en": "Internal links", "done": False},
]


def _utc_now() -> str:
    """ISO timestamp in UTC."""
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    """Generate short unique id."""
    return uuid.uuid4().hex[:12]


def _default_checklist_json() -> str:
    """Serialize default checklist template."""
    return json.dumps(DEFAULT_CHECKLIST, ensure_ascii=False)


def _assignee_payload(user_id: Optional[int]) -> Optional[Dict[str, Any]]:
    """Resolve assignee user id to display dict for Kanban cards."""
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


def _parse_item_row(row: Any) -> Dict[str, Any]:
    """Deserialize checklist JSON on a calendar item row."""
    item = dict(row)
    try:
        item["checklist"] = json.loads(item.get("checklist") or "[]")
    except json.JSONDecodeError:
        item["checklist"] = [dict(x) for x in DEFAULT_CHECKLIST]
    raw_snap = item.get("scrape_snapshot")
    if raw_snap and isinstance(raw_snap, str):
        try:
            item["scrape_snapshot"] = json.loads(raw_snap)
        except json.JSONDecodeError:
            item["scrape_snapshot"] = None
    raw_links = item.get("suggested_links")
    if raw_links and isinstance(raw_links, str):
        try:
            item["suggested_links"] = json.loads(raw_links)
        except json.JSONDecodeError:
            item["suggested_links"] = []
    elif not item.get("suggested_links"):
        item["suggested_links"] = []
    item["status"] = normalize_kanban_status(item.get("status"))
    item["assignee"] = _assignee_payload(item.get("assigned_user_id"))
    return item


def _next_campaign_name(project_slug: str) -> str:
    """Auto-name: کمپین 1, کمپین 2, … per project."""
    conn = get_connection()
    count = conn.execute(
        "SELECT COUNT(*) AS c FROM campaigns WHERE project_slug = ?",
        (project_slug,),
    ).fetchone()["c"]
    return f"کمپین {count + 1}"


def _backfill_legacy_campaigns(project_slug: str) -> None:
    """
    Migrate boards/items without campaign_id into auto-named campaigns.

    Input:
        project_slug: Project to scan.

    Output:
        Legacy rows linked to new campaigns (idempotent).
    """
    conn = get_connection()
    boards = conn.execute(
        """
        SELECT id FROM calendar_boards
        WHERE project_slug = ? AND (campaign_id IS NULL OR campaign_id = '')
        """,
        (project_slug,),
    ).fetchall()
    if not boards:
        return
    now = _utc_now()
    for row in boards:
        campaign_id = _new_id()
        name = _next_campaign_name(project_slug)
        conn.execute(
            """
            INSERT INTO campaigns (id, project_slug, name, sort_order, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (campaign_id, project_slug, name, 0, now, now),
        )
        conn.execute(
            "UPDATE calendar_boards SET campaign_id = ?, updated_at = ? WHERE id = ?",
            (campaign_id, now, row["id"]),
        )
        conn.execute(
            "UPDATE calendar_items SET campaign_id = ? WHERE board_id = ?",
            (campaign_id, row["id"]),
        )
    conn.commit()


def create_campaign(
    project_slug: str,
    name: str,
    *,
    sort_order: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Create a campaign bucket for a project.

    Input:
        project_slug: Project scope.
        name: Display name (e.g. کمپین ۱).

    Output:
        Campaign dict.
    """
    conn = get_connection()
    campaign_id = _new_id()
    now = _utc_now()
    if sort_order is None:
        row = conn.execute(
            "SELECT COALESCE(MAX(sort_order), -1) + 1 AS n FROM campaigns WHERE project_slug = ?",
            (project_slug,),
        ).fetchone()
        sort_order = int(row["n"])
    conn.execute(
        """
        INSERT INTO campaigns (id, project_slug, name, sort_order, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (campaign_id, project_slug, name.strip(), sort_order, now, now),
    )
    conn.commit()
    return get_campaign(campaign_id)


def get_campaign(campaign_id: str) -> Optional[Dict[str, Any]]:
    """Load one campaign by id."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
    return dict(row) if row else None


def list_campaigns(project_slug: str) -> List[Dict[str, Any]]:
    """
    List campaigns for a project with item counts.

    Output:
        Sorted campaigns (sort_order, then created_at).
    """
    _backfill_legacy_campaigns(project_slug)
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT c.*, COUNT(i.id) AS item_count
        FROM campaigns c
        LEFT JOIN calendar_items i ON i.campaign_id = c.id
        WHERE c.project_slug = ?
        GROUP BY c.id
        ORDER BY c.sort_order ASC, c.created_at ASC
        """,
        (project_slug,),
    ).fetchall()
    return [dict(r) for r in rows]


def ensure_campaign_for_import(
    project_slug: Optional[str],
    campaign_id: Optional[str] = None,
) -> Optional[str]:
    """
    Resolve campaign id for a new board import.

    Input:
        project_slug: Required for auto campaign.
        campaign_id: Existing campaign or None to auto-create.

    Output:
        campaign_id or None when no project scope.
    """
    if not project_slug:
        return campaign_id
    if campaign_id:
        existing = get_campaign(campaign_id)
        if existing and existing.get("project_slug") == project_slug:
            return campaign_id
    created = create_campaign(project_slug, _next_campaign_name(project_slug))
    return created["id"]


def reorder_campaigns(project_slug: str, ordered_ids: List[str]) -> List[Dict[str, Any]]:
    """Persist drag-reordered campaign tabs."""
    conn = get_connection()
    now = _utc_now()
    for idx, cid in enumerate(ordered_ids):
        conn.execute(
            "UPDATE campaigns SET sort_order = ?, updated_at = ? WHERE id = ? AND project_slug = ?",
            (idx, now, cid, project_slug),
        )
    conn.commit()
    return list_campaigns(project_slug)


def get_campaign_board(campaign_id: str) -> Optional[Dict[str, Any]]:
    """
    Load Kanban view for a campaign (all items across boards).

    Output:
        Pseudo-board dict with items list.
    """
    campaign = get_campaign(campaign_id)
    if not campaign:
        return None
    conn = get_connection()
    item_rows = conn.execute(
        """
        SELECT * FROM calendar_items
        WHERE campaign_id = ?
        ORDER BY sort_order ASC, publish_date ASC
        """,
        (campaign_id,),
    ).fetchall()
    items = [_parse_item_row(r) for r in item_rows]
    return {
        "id": campaign_id,
        "campaign_id": campaign_id,
        "project_slug": campaign["project_slug"],
        "title": campaign["name"],
        "items": items,
    }


def create_board_from_calendar_rows(
    rows: List[Dict[str, Any]],
    *,
    project_slug: Optional[str] = None,
    job_id: Optional[str] = None,
    campaign_id: Optional[str] = None,
    title: str = "Content calendar",
    created_by: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Import calendar rows into a new Kanban board.

    Input:
        rows: Cluster pipeline calendar entries.
        project_slug: Optional project scope.
        job_id: Source background job id.
        campaign_id: Target campaign (auto-created per project if omitted).

    Output:
        Board dict with items list.
    """
    resolved_campaign = ensure_campaign_for_import(project_slug, campaign_id)
    board_id = _new_id()
    now = _utc_now()
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO calendar_boards (id, project_slug, job_id, campaign_id, title, created_by, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (board_id, project_slug, job_id, resolved_campaign, title, created_by, now, now),
    )

    items: List[Dict[str, Any]] = []
    for idx, row in enumerate(rows):
        item_id = _new_id()
        keywords = row.get("keywords") or []
        if isinstance(keywords, list):
            kw_str = " | ".join(str(k) for k in keywords)
        else:
            kw_str = str(keywords)
        h2 = row.get("h2_headings") or []
        if isinstance(h2, list):
            h2_str = " | ".join(str(h) for h in h2)
        else:
            h2_str = str(h2)

        status = normalize_kanban_status(row.get("status") or "pending")

        item = {
            "id": item_id,
            "board_id": board_id,
            "campaign_id": resolved_campaign,
            "sort_order": idx,
            "publish_date": row.get("publish_date"),
            "title": row.get("suggested_title") or row.get("article_title") or "",
            "h1_title": row.get("article_title") or row.get("suggested_title") or "",
            "h2_headings": h2_str,
            "meta_description": row.get("meta_description") or "",
            "keywords": kw_str,
            "difficulty_label": row.get("difficulty_label") or "",
            "difficulty_score": row.get("difficulty_score"),
            "avg_volume": row.get("avg_volume"),
            "content_type": row.get("content_type") or "",
            "search_intent": row.get("search_intent") or "",
            "status": status,
            "notes": row.get("notes") or "",
            "checklist": json.loads(_default_checklist_json()),
        }
        conn.execute(
            """
            INSERT INTO calendar_items (
                id, board_id, campaign_id, sort_order, publish_date, title, h1_title, h2_headings,
                meta_description, keywords, difficulty_label, difficulty_score, avg_volume,
                content_type, search_intent, status, notes, checklist, assigned_user_id, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item_id,
                board_id,
                resolved_campaign,
                idx,
                item["publish_date"],
                item["title"],
                item["h1_title"],
                item["h2_headings"],
                item["meta_description"],
                item["keywords"],
                item["difficulty_label"],
                item["difficulty_score"],
                item["avg_volume"],
                item["content_type"],
                item["search_intent"],
                item["status"],
                item["notes"],
                json.dumps(item["checklist"], ensure_ascii=False),
                None,
                now,
            ),
        )
        items.append(item)

    conn.commit()
    board = get_board(board_id)
    if board and resolved_campaign:
        board["campaign_id"] = resolved_campaign
    return board


def get_board(board_id: str) -> Optional[Dict[str, Any]]:
    """Load board with all items ordered by sort_order."""
    conn = get_connection()
    board_row = conn.execute("SELECT * FROM calendar_boards WHERE id = ?", (board_id,)).fetchone()
    if not board_row:
        return None

    item_rows = conn.execute(
        "SELECT * FROM calendar_items WHERE board_id = ? ORDER BY sort_order ASC",
        (board_id,),
    ).fetchall()

    board = dict(board_row)
    board["items"] = [_parse_item_row(r) for r in item_rows]
    return board


def get_board_by_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Find board created from a cluster job."""
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM calendar_boards WHERE job_id = ? ORDER BY created_at DESC LIMIT 1",
        (job_id,),
    ).fetchone()
    if not row:
        return None
    return get_board(row["id"])


def list_boards(project_slug: Optional[str] = None) -> List[Dict[str, Any]]:
    """List boards, optionally filtered by project."""
    conn = get_connection()
    if project_slug:
        rows = conn.execute(
            """
            SELECT id, project_slug, job_id, campaign_id, title, created_at, updated_at
            FROM calendar_boards WHERE project_slug = ? ORDER BY updated_at DESC
            """,
            (project_slug,),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT id, project_slug, job_id, campaign_id, title, created_at, updated_at
            FROM calendar_boards ORDER BY updated_at DESC LIMIT 50
            """
        ).fetchall()
    return [dict(r) for r in rows]


def update_item(
    item_id: str,
    *,
    status: Optional[str] = None,
    notes: Optional[str] = None,
    checklist: Optional[List[Dict[str, Any]]] = None,
    campaign_id: Optional[str] = None,
    title: Optional[str] = None,
    h1_title: Optional[str] = None,
    h2_headings: Optional[str] = None,
    meta_description: Optional[str] = None,
    url: Optional[str] = None,
    scrape_snapshot: Optional[Dict[str, Any]] = None,
    last_scraped_at: Optional[str] = None,
    suggested_links: Optional[List[Dict[str, Any]]] = None,
    assigned_user_id: Optional[int] = ...,
    updated_by: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """
    Update Kanban card fields (status, notes, checklist, campaign, SEO fields).

    Output:
        Updated item dict or None if not found.
    """
    conn = get_connection()
    row = conn.execute("SELECT * FROM calendar_items WHERE id = ?", (item_id,)).fetchone()
    if not row:
        return None

    if status is not None:
        status = normalize_kanban_status(status)
        if status not in KANBAN_STATUSES:
            raise ValueError(f"Invalid status: {status}")

    if campaign_id is not None:
        camp = get_campaign(campaign_id)
        if not camp:
            raise ValueError(f"Campaign not found: {campaign_id}")

    project_slug = get_item_project_slug(item_id) or ""

    fields = []
    values: List[Any] = []
    if status is not None:
        fields.append("status = ?")
        values.append(status)
    if notes is not None:
        fields.append("notes = ?")
        values.append(notes)
    if checklist is not None:
        fields.append("checklist = ?")
        values.append(json.dumps(checklist, ensure_ascii=False))
    if campaign_id is not None:
        fields.append("campaign_id = ?")
        values.append(campaign_id)
    if title is not None:
        fields.append("title = ?")
        values.append(title)
    if h1_title is not None:
        fields.append("h1_title = ?")
        values.append(h1_title)
    if h2_headings is not None:
        fields.append("h2_headings = ?")
        values.append(h2_headings)
    if meta_description is not None:
        fields.append("meta_description = ?")
        values.append(meta_description)
    if url is not None:
        fields.append("url = ?")
        values.append(url)
    if scrape_snapshot is not None:
        fields.append("scrape_snapshot = ?")
        values.append(json.dumps(scrape_snapshot, ensure_ascii=False))
    if last_scraped_at is not None:
        fields.append("last_scraped_at = ?")
        values.append(last_scraped_at)
    if suggested_links is not None:
        fields.append("suggested_links = ?")
        values.append(json.dumps(suggested_links, ensure_ascii=False))
    if assigned_user_id is not ...:
        assignee = validate_assignee_for_project(project_slug, assigned_user_id)
        fields.append("assigned_user_id = ?")
        values.append(assignee)
    if updated_by is not None:
        fields.append("updated_by = ?")
        values.append(updated_by)

    now = _utc_now()
    fields.append("updated_at = ?")
    values.append(now)
    values.append(item_id)

    conn.execute(f"UPDATE calendar_items SET {', '.join(fields)} WHERE id = ?", values)
    conn.execute(
        "UPDATE calendar_boards SET updated_at = ? WHERE id = ?",
        (now, row["board_id"]),
    )
    conn.commit()

    updated = conn.execute("SELECT * FROM calendar_items WHERE id = ?", (item_id,)).fetchone()
    return _parse_item_row(updated)


def get_item(item_id: str) -> Optional[Dict[str, Any]]:
    """Load one calendar item by id."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM calendar_items WHERE id = ?", (item_id,)).fetchone()
    return _parse_item_row(row) if row else None


def get_item_project_slug(item_id: str) -> Optional[str]:
    """
    Resolve project slug for an item (via campaign or board).

    Output:
        project_slug or None.
    """
    conn = get_connection()
    row = conn.execute(
        """
        SELECT b.project_slug, i.campaign_id
        FROM calendar_items i
        JOIN calendar_boards b ON b.id = i.board_id
        WHERE i.id = ?
        """,
        (item_id,),
    ).fetchone()
    if not row:
        return None
    if row["project_slug"]:
        return row["project_slug"]
    if row["campaign_id"]:
        camp = get_campaign(row["campaign_id"])
        return camp.get("project_slug") if camp else None
    return None


def delete_item(item_id: str) -> bool:
    """
    Permanently remove a calendar item.

    Output:
        True if deleted, False if not found.
    """
    conn = get_connection()
    row = conn.execute("SELECT board_id FROM calendar_items WHERE id = ?", (item_id,)).fetchone()
    if not row:
        return False
    now = _utc_now()
    conn.execute("DELETE FROM calendar_items WHERE id = ?", (item_id,))
    conn.execute(
        "UPDATE calendar_boards SET updated_at = ? WHERE id = ?",
        (now, row["board_id"]),
    )
    conn.commit()
    return True


def delete_campaign(campaign_id: str) -> bool:
    """
    Delete campaign and all its calendar items.

    Input:
        campaign_id: Campaign to remove.

    Output:
        True if deleted, False if not found.
    """
    conn = get_connection()
    camp = get_campaign(campaign_id)
    if not camp:
        return False
    now = _utc_now()
    conn.execute("DELETE FROM calendar_items WHERE campaign_id = ?", (campaign_id,))
    board_rows = conn.execute(
        "SELECT id FROM calendar_boards WHERE campaign_id = ?",
        (campaign_id,),
    ).fetchall()
    for brow in board_rows:
        remaining = conn.execute(
            "SELECT COUNT(*) AS c FROM calendar_items WHERE board_id = ?",
            (brow["id"],),
        ).fetchone()["c"]
        if remaining == 0:
            conn.execute("DELETE FROM calendar_boards WHERE id = ?", (brow["id"],))
        else:
            conn.execute(
                "UPDATE calendar_boards SET campaign_id = NULL, updated_at = ? WHERE id = ?",
                (now, brow["id"]),
            )
    conn.execute("DELETE FROM campaigns WHERE id = ?", (campaign_id,))
    conn.commit()
    return True
