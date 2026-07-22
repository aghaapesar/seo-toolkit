"""
SQLite registry for per-URL knowledge export state.

Input:
    project_slug, page URL, export metadata.

Output:
    CRUD for registry rows; staleness reports; download / re-index flags.
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
    needs_reindex: Optional[bool] = None,
    change_reason: Optional[str] = None,
) -> str:
    """
    Insert or update registry row for one exported URL.

    Input:
        needs_reindex: When True, flags MD for selective RAG re-index.
        change_reason: new | content_updated | sitemap_updated | ''

    Output:
        Row id (UUID).
    """
    status = status if status in _VALID_STATUS else "exported"
    relative_path = _normalize_registry_path(relative_path)
    conn = get_connection()
    row = conn.execute(
        "SELECT id, content_hash, needs_reindex FROM knowledge_export_pages "
        "WHERE project_slug = ? AND url = ?",
        (project_slug, url),
    ).fetchone()
    now = _now_iso()
    exported_at = now if status == "exported" else None

    # Auto-detect content change when exporting successfully
    auto_reindex = False
    auto_reason = ""
    if status == "exported" and content_hash:
        if not row:
            auto_reindex = True
            auto_reason = "new"
        elif (row["content_hash"] or "") != content_hash:
            auto_reindex = True
            auto_reason = "content_updated"

    if needs_reindex is None:
        flag = 1 if auto_reindex else (int(row["needs_reindex"]) if row else 0)
    else:
        flag = 1 if needs_reindex else 0

    if change_reason is None:
        reason = auto_reason or ""
    else:
        reason = change_reason

    if row:
        # Keep existing reindex flag if already set and we are not clearing
        if needs_reindex is None and row["needs_reindex"] and not auto_reindex:
            flag = 1
            # preserve prior reason unless we have a new one
            if not reason:
                prev = conn.execute(
                    "SELECT change_reason FROM knowledge_export_pages WHERE id = ?",
                    (row["id"],),
                ).fetchone()
                reason = (prev["change_reason"] if prev else "") or ""

        conn.execute(
            """
            UPDATE knowledge_export_pages SET
                page_type = ?, slug = ?, relative_path = ?, title = ?,
                content_hash = ?, sitemap_lastmod = ?, status = ?,
                exported_at = COALESCE(?, exported_at),
                needs_reindex = ?, change_reason = ?,
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
                flag,
                reason,
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
            content_hash, sitemap_lastmod, status, exported_at,
            needs_reindex, change_reason, updated_at, error
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            flag,
            reason,
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


def flag_stale_from_sitemap(
    project_slug: str,
    url_lastmod: Dict[str, str],
) -> int:
    """
    Mark registry rows as stale + needs_reindex when sitemap lastmod advanced.

    Output:
        Number of rows flagged.
    """
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, url, sitemap_lastmod, status FROM knowledge_export_pages WHERE project_slug = ?",
        (project_slug,),
    ).fetchall()
    now = _now_iso()
    flagged = 0
    for row in rows:
        url = row["url"]
        if url not in url_lastmod:
            continue
        cur_lm = (url_lastmod.get(url) or "").strip()
        reg_lm = (row["sitemap_lastmod"] or "").strip()
        if cur_lm and reg_lm and cur_lm != reg_lm:
            conn.execute(
                """
                UPDATE knowledge_export_pages SET
                    status = 'stale',
                    needs_reindex = 1,
                    change_reason = 'sitemap_updated',
                    updated_at = ?
                WHERE id = ?
                """,
                (now, row["id"]),
            )
            flagged += 1
    conn.commit()
    return flagged


def mark_reindexed(
    project_slug: str,
    *,
    relative_paths: Optional[List[str]] = None,
    all_flagged: bool = False,
) -> int:
    """
    Clear needs_reindex after user sends files to RAG.

    Input:
        relative_paths: Specific page paths under knowledge_export/.
        all_flagged: Clear every needs_reindex=1 row for the project.

    Output:
        Number of rows cleared.
    """
    conn = get_connection()
    now = _now_iso()
    if all_flagged:
        cur = conn.execute(
            """
            UPDATE knowledge_export_pages SET
                needs_reindex = 0, change_reason = '', rag_indexed_at = ?, updated_at = ?
            WHERE project_slug = ? AND needs_reindex = 1
            """,
            (now, now, project_slug),
        )
        conn.commit()
        return cur.rowcount or 0

    count = 0
    for raw in relative_paths or []:
        rel = _normalize_registry_path(raw)
        cur = conn.execute(
            """
            UPDATE knowledge_export_pages SET
                needs_reindex = 0, change_reason = '', rag_indexed_at = ?, updated_at = ?
            WHERE project_slug = ? AND relative_path = ?
            """,
            (now, now, project_slug, rel),
        )
        count += cur.rowcount or 0
    conn.commit()
    return count


def list_pages(
    project_slug: str,
    *,
    status: Optional[str] = None,
    needs_reindex: Optional[bool] = None,
    limit: int = 5000,
) -> List[Dict[str, Any]]:
    """List registry rows for project UI (optional reindex filter)."""
    conn = get_connection()
    clauses = ["project_slug = ?"]
    params: List[Any] = [project_slug]
    if status:
        clauses.append("status = ?")
        params.append(status)
    if needs_reindex is not None:
        clauses.append("needs_reindex = ?")
        params.append(1 if needs_reindex else 0)
    params.append(limit)
    where = " AND ".join(clauses)
    rows = conn.execute(
        f"""
        SELECT * FROM knowledge_export_pages
        WHERE {where}
        ORDER BY needs_reindex DESC, updated_at DESC LIMIT ?
        """,
        params,
    ).fetchall()
    return [dict(r) for r in rows]


def compute_staleness_report(
    project_slug: str,
    url_lastmod: Dict[str, str],
) -> Dict[str, Any]:
    """
    Compare sitemap lastmod map with registry for analyze-time report.

    Also persists stale flags via flag_stale_from_sitemap.

    Output:
        Counts and URL lists for new/stale/unchanged + flagged_count.
    """
    flagged = flag_stale_from_sitemap(project_slug, url_lastmod)

    conn = get_connection()
    rows = conn.execute(
        "SELECT url, sitemap_lastmod, content_hash, status, needs_reindex, relative_path "
        "FROM knowledge_export_pages WHERE project_slug = ?",
        (project_slug,),
    ).fetchall()
    registry = {r["url"]: dict(r) for r in rows}

    new_urls: List[str] = []
    stale_urls: List[str] = []
    unchanged_urls: List[str] = []
    changed_paths: List[str] = []

    for url, lastmod in url_lastmod.items():
        reg = registry.get(url)
        if not reg or reg.get("status") in ("failed", "skipped_noindex", "skipped_filter"):
            new_urls.append(url)
            continue
        reg_lm = (reg.get("sitemap_lastmod") or "").strip()
        cur_lm = (lastmod or "").strip()
        if cur_lm and reg_lm and cur_lm != reg_lm:
            stale_urls.append(url)
            if reg.get("relative_path"):
                changed_paths.append(reg["relative_path"])
        elif not reg.get("content_hash"):
            new_urls.append(url)
        else:
            unchanged_urls.append(url)

    for reg in registry.values():
        if reg.get("needs_reindex") and reg.get("relative_path"):
            if reg["relative_path"] not in changed_paths:
                changed_paths.append(reg["relative_path"])

    removed = [u for u in registry if u not in url_lastmod]

    return {
        "total_sitemap_urls": len(url_lastmod),
        "registry_count": len(registry),
        "new_count": len(new_urls),
        "stale_count": len(stale_urls),
        "unchanged_count": len(unchanged_urls),
        "removed_count": len(removed),
        "flagged_reindex_count": flagged,
        "needs_reindex_count": sum(1 for r in registry.values() if r.get("needs_reindex")),
        "changed_paths_sample": changed_paths[:40],
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
