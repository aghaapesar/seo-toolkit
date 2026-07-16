"""
SQLite registry for per-URL knowledge export state.

Input:
    project_slug, page URL, export metadata.

Output:
    CRUD for registry rows; staleness reports; download tracking.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from web.app.services.database import get_connection

_VALID_STATUS = frozenset(
    {
        "new",
        "exported",
        "stale",
        "failed",
        "skipped_noindex",
        "skipped_filter",
        "skipped_unchanged",
    }
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_registry_path(path: str) -> str:
    """Normalize to path relative to knowledge_export output dir."""
    p = (path or "").replace("\\", "/").lstrip("/")
    if "knowledge_export/" in p:
        return p.split("knowledge_export/", 1)[-1]
    return p


def upsert_page(
    *,
    project_slug: str,
    url: str,
    page_type: str = "other",
    slug: str = "",
    relative_path: str = "",
    title: str = "",
    content_hash: str = "",
    sitemap_lastmod: str = "",
    status: str = "exported",
    error: str = "",
) -> str:
    """
    Insert or update registry row for one exported URL.

    Output:
        Row id (UUID).
    """
    status = status if status in _VALID_STATUS else "exported"
    relative_path = _normalize_registry_path(relative_path)
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM knowledge_export_pages WHERE project_slug = ? AND url = ?",
        (project_slug, url),
    ).fetchone()
    now = _now_iso()
    exported_at = now if status == "exported" else None

    if row:
        conn.execute(
            """
            UPDATE knowledge_export_pages SET
                page_type = ?, slug = ?, relative_path = ?, title = ?,
                content_hash = ?, sitemap_lastmod = ?, status = ?,
                exported_at = COALESCE(?, exported_at),
                error = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                page_type,
                slug,
                relative_path,
                title,
                content_hash,
                sitemap_lastmod,
                status,
                exported_at,
                error,
                now,
                row["id"],
            ),
        )
        conn.commit()
        return row["id"]

    row_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO knowledge_export_pages (
            id, project_slug, url, page_type, slug, relative_path, title,
            content_hash, sitemap_lastmod, status, exported_at, updated_at, error
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row_id,
            project_slug,
            url,
            page_type,
            slug,
            relative_path,
            title,
            content_hash,
            sitemap_lastmod,
            status,
            exported_at,
            now,
            error,
        ),
    )
    conn.commit()
    return row_id


def mark_downloaded_by_path(project_slug: str, relative_path: str) -> bool:
    """
    Set first_downloaded_at on first panel download.

    Output:
        True when a row was updated.
    """
    rel = _normalize_registry_path(relative_path)
    conn = get_connection()
    row = conn.execute(
        """
        SELECT id, first_downloaded_at FROM knowledge_export_pages
        WHERE project_slug = ? AND relative_path = ?
        """,
        (project_slug, rel),
    ).fetchone()
    if not row or row["first_downloaded_at"]:
        return False
    conn.execute(
        "UPDATE knowledge_export_pages SET first_downloaded_at = ?, updated_at = ? WHERE id = ?",
        (_now_iso(), _now_iso(), row["id"]),
    )
    conn.commit()
    return True


def list_pages(
    project_slug: str,
    *,
    status: Optional[str] = None,
    limit: int = 5000,
) -> List[Dict[str, Any]]:
    """List registry rows for project UI."""
    conn = get_connection()
    if status:
        rows = conn.execute(
            """
            SELECT * FROM knowledge_export_pages
            WHERE project_slug = ? AND status = ?
            ORDER BY updated_at DESC LIMIT ?
            """,
            (project_slug, status, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT * FROM knowledge_export_pages
            WHERE project_slug = ?
            ORDER BY updated_at DESC LIMIT ?
            """,
            (project_slug, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def compute_staleness_report(
    project_slug: str,
    url_lastmod: Dict[str, str],
) -> Dict[str, Any]:
    """
    Compare sitemap lastmod map with registry for analyze-time report.

    Output:
        Counts and URL lists for new/stale/unchanged.
    """
    conn = get_connection()
    rows = conn.execute(
        "SELECT url, sitemap_lastmod, content_hash, status FROM knowledge_export_pages WHERE project_slug = ?",
        (project_slug,),
    ).fetchall()
    registry = {r["url"]: dict(r) for r in rows}

    new_urls: List[str] = []
    stale_urls: List[str] = []
    unchanged_urls: List[str] = []

    for url, lastmod in url_lastmod.items():
        reg = registry.get(url)
        if not reg or reg.get("status") in ("failed", "skipped_noindex", "skipped_filter"):
            new_urls.append(url)
            continue
        reg_lm = (reg.get("sitemap_lastmod") or "").strip()
        cur_lm = (lastmod or "").strip()
        if cur_lm and reg_lm and cur_lm != reg_lm:
            stale_urls.append(url)
        elif not reg.get("content_hash"):
            new_urls.append(url)
        else:
            unchanged_urls.append(url)

    # URLs in registry but not in sitemap anymore
    removed = [u for u in registry if u not in url_lastmod]

    return {
        "total_sitemap_urls": len(url_lastmod),
        "registry_count": len(registry),
        "new_count": len(new_urls),
        "stale_count": len(stale_urls),
        "unchanged_count": len(unchanged_urls),
        "removed_count": len(removed),
        "new_urls_sample": new_urls[:20],
        "stale_urls_sample": stale_urls[:20],
    }


def get_registry_row(project_slug: str, url: str) -> Optional[Dict[str, Any]]:
    """Fetch one registry row by URL."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM knowledge_export_pages WHERE project_slug = ? AND url = ?",
        (project_slug, url),
    ).fetchone()
    return dict(row) if row else None
