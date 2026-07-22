"""
SQLite database bootstrap for users and content calendar boards.

Input:
    DB path (default data/seo_toolkit.db).

Output:
    Connection with schema migrated on every open (idempotent).
"""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Optional

DB_PATH = Path("data/seo_toolkit.db")
_lock = threading.Lock()
_initialized = False
_schema_migrated = False

# Default SQLite busy wait (ms) when another connection holds a write lock.
SQLITE_BUSY_TIMEOUT_MS = 30_000

# Base schema for fresh installs. Index/column upgrades run in _migrate_schema().
SCHEMA_SQL = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    display_name TEXT,
    is_admin INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS project_members (
    user_id INTEGER NOT NULL,
    project_slug TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'editor',
    PRIMARY KEY (user_id, project_slug),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS campaigns (
    id TEXT PRIMARY KEY,
    project_slug TEXT NOT NULL,
    name TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS calendar_boards (
    id TEXT PRIMARY KEY,
    project_slug TEXT,
    job_id TEXT,
    campaign_id TEXT,
    title TEXT NOT NULL,
    created_by INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS calendar_items (
    id TEXT PRIMARY KEY,
    board_id TEXT NOT NULL,
    campaign_id TEXT,
    url TEXT,
    last_scraped_at TEXT,
    scrape_snapshot TEXT,
    suggested_links TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    publish_date TEXT,
    title TEXT,
    h1_title TEXT,
    h2_headings TEXT,
    meta_description TEXT,
    keywords TEXT,
    difficulty_label TEXT,
    difficulty_score REAL,
    avg_volume REAL,
    content_type TEXT,
    search_intent TEXT,
    status TEXT NOT NULL DEFAULT 'planned',
    notes TEXT,
    checklist TEXT,
    assigned_user_id INTEGER,
    updated_by INTEGER,
    updated_at TEXT,
    FOREIGN KEY (board_id) REFERENCES calendar_boards(id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_calendar_items_board ON calendar_items(board_id);
CREATE INDEX IF NOT EXISTS idx_calendar_boards_project ON calendar_boards(project_slug);
"""


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    """Return True when table is present."""
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    """Return column names for an existing SQLite table."""
    if not _table_exists(conn, table):
        return set()
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row[1] for row in rows}


def _migrate_schema(conn: sqlite3.Connection) -> None:
    """
    Apply incremental schema changes for existing databases.

    Input:
        Open SQLite connection.

    Output:
        Schema updated in place (idempotent).
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS campaigns (
            id TEXT PRIMARY KEY,
            project_slug TEXT NOT NULL,
            name TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    board_cols = _table_columns(conn, "calendar_boards")
    if _table_exists(conn, "calendar_boards") and "campaign_id" not in board_cols:
        conn.execute("ALTER TABLE calendar_boards ADD COLUMN campaign_id TEXT")

    item_cols = _table_columns(conn, "calendar_items")
    if _table_exists(conn, "calendar_items") and "campaign_id" not in item_cols:
        conn.execute("ALTER TABLE calendar_items ADD COLUMN campaign_id TEXT")
    if _table_exists(conn, "calendar_items") and "url" not in item_cols:
        conn.execute("ALTER TABLE calendar_items ADD COLUMN url TEXT")
    if _table_exists(conn, "calendar_items") and "last_scraped_at" not in item_cols:
        conn.execute("ALTER TABLE calendar_items ADD COLUMN last_scraped_at TEXT")
    if _table_exists(conn, "calendar_items") and "scrape_snapshot" not in item_cols:
        conn.execute("ALTER TABLE calendar_items ADD COLUMN scrape_snapshot TEXT")
    item_cols = _table_columns(conn, "calendar_items")
    if _table_exists(conn, "calendar_items") and "suggested_links" not in item_cols:
        conn.execute("ALTER TABLE calendar_items ADD COLUMN suggested_links TEXT")
    item_cols = _table_columns(conn, "calendar_items")
    if _table_exists(conn, "calendar_items") and "assigned_user_id" not in item_cols:
        conn.execute(
            "ALTER TABLE calendar_items ADD COLUMN assigned_user_id INTEGER REFERENCES users(id)"
        )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS site_index_runs (
            id TEXT PRIMARY KEY,
            project_slug TEXT NOT NULL,
            job_id TEXT,
            status TEXT NOT NULL DEFAULT 'queued',
            sitemap_url TEXT,
            total_urls INTEGER NOT NULL DEFAULT 0,
            processed_count INTEGER NOT NULL DEFAULT 0,
            success_count INTEGER NOT NULL DEFAULT 0,
            last_url TEXT,
            urls_json TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS site_pages (
            id TEXT PRIMARY KEY,
            project_slug TEXT NOT NULL,
            url TEXT NOT NULL,
            url_normalized TEXT NOT NULL,
            page_type TEXT,
            title TEXT,
            meta_description TEXT,
            h1 TEXT,
            body_text TEXT,
            body_excerpt TEXT,
            product_name TEXT,
            product_price TEXT,
            product_sku TEXT,
            categories TEXT,
            json_ld TEXT,
            internal_links TEXT,
            scrape_status TEXT,
            scrape_error TEXT,
            content_hash TEXT,
            scraped_at TEXT,
            updated_at TEXT,
            UNIQUE(project_slug, url_normalized)
        )
        """
    )

    # Safe to create indexes only after columns exist.
    conn.execute("CREATE INDEX IF NOT EXISTS idx_site_pages_project ON site_pages(project_slug)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_site_pages_type ON site_pages(project_slug, page_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_site_index_runs_project ON site_index_runs(project_slug)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_calendar_items_campaign ON calendar_items(campaign_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_campaigns_project ON campaigns(project_slug)")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS keyword_uploads (
            id TEXT PRIMARY KEY,
            project_slug TEXT NOT NULL,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            row_count INTEGER NOT NULL DEFAULT 0,
            uploaded_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS product_gap_snapshots (
            id TEXT PRIMARY KEY,
            project_slug TEXT NOT NULL,
            analyzed_at TEXT NOT NULL,
            upload_count INTEGER NOT NULL DEFAULT 0,
            site_product_count INTEGER NOT NULL DEFAULT 0,
            on_site_count INTEGER NOT NULL DEFAULT 0,
            missing_count INTEGER NOT NULL DEFAULT 0,
            results_json TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_keyword_uploads_project ON keyword_uploads(project_slug)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_product_gap_project ON product_gap_snapshots(project_slug)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS product_gap_exclusions (
            id TEXT PRIMARY KEY,
            project_slug TEXT NOT NULL,
            keyword_normalized TEXT NOT NULL,
            keyword_original TEXT,
            excluded_at TEXT NOT NULL,
            UNIQUE(project_slug, keyword_normalized)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_gap_exclusions_project ON product_gap_exclusions(project_slug)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS product_gap_archived (
            id TEXT PRIMARY KEY,
            project_slug TEXT NOT NULL,
            list_type TEXT NOT NULL DEFAULT 'product_procurement',
            keyword_normalized TEXT NOT NULL,
            keyword_original TEXT,
            row_json TEXT,
            archived_at TEXT NOT NULL,
            UNIQUE(project_slug, list_type, keyword_normalized)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_gap_archived_project ON product_gap_archived(project_slug, list_type)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS product_gap_manual_rows (
            id TEXT PRIMARY KEY,
            project_slug TEXT NOT NULL,
            keyword_normalized TEXT NOT NULL,
            keyword_original TEXT,
            target_list TEXT NOT NULL,
            row_json TEXT,
            updated_at TEXT NOT NULL,
            UNIQUE(project_slug, keyword_normalized)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_gap_manual_project ON product_gap_manual_rows(project_slug)"
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS gsc_performance_uploads (
            id TEXT PRIMARY KEY,
            project_slug TEXT NOT NULL,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            page_count INTEGER NOT NULL DEFAULT 0,
            query_count INTEGER NOT NULL DEFAULT 0,
            uploaded_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_gsc_uploads_project ON gsc_performance_uploads(project_slug)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS link_graph_snapshots (
            id TEXT PRIMARY KEY,
            project_slug TEXT NOT NULL,
            analyzed_at TEXT NOT NULL,
            node_count INTEGER NOT NULL DEFAULT 0,
            results_json TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_link_graph_project ON link_graph_snapshots(project_slug)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS link_recommendation_runs (
            id TEXT PRIMARY KEY,
            project_slug TEXT NOT NULL,
            analyzed_at TEXT NOT NULL,
            target_count INTEGER NOT NULL DEFAULT 0,
            results_json TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_link_reco_project ON link_recommendation_runs(project_slug)"
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS project_tasks (
            id TEXT PRIMARY KEY,
            project_slug TEXT NOT NULL,
            title TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',
            priority TEXT NOT NULL DEFAULT 'medium',
            tags TEXT NOT NULL DEFAULT '',
            due_date TEXT NOT NULL DEFAULT '',
            assigned_user_id INTEGER,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_project_tasks_slug ON project_tasks(project_slug, status)"
    )

    task_cols = _table_columns(conn, "project_tasks")
    if _table_exists(conn, "project_tasks"):
        if "priority" not in task_cols:
            conn.execute(
                "ALTER TABLE project_tasks ADD COLUMN priority TEXT NOT NULL DEFAULT 'medium'"
            )
        if "tags" not in task_cols:
            conn.execute("ALTER TABLE project_tasks ADD COLUMN tags TEXT NOT NULL DEFAULT ''")
        if "due_date" not in task_cols:
            conn.execute("ALTER TABLE project_tasks ADD COLUMN due_date TEXT NOT NULL DEFAULT ''")
        if "assigned_user_id" not in task_cols:
            conn.execute(
                "ALTER TABLE project_tasks ADD COLUMN assigned_user_id INTEGER REFERENCES users(id)"
            )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS project_task_subtasks (
            id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            title TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0,
            assigned_user_id INTEGER,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (task_id) REFERENCES project_tasks(id) ON DELETE CASCADE,
            FOREIGN KEY (assigned_user_id) REFERENCES users(id)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_project_subtasks_task ON project_task_subtasks(task_id)"
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS knowledge_export_pages (
            id TEXT PRIMARY KEY,
            project_slug TEXT NOT NULL,
            url TEXT NOT NULL,
            page_type TEXT NOT NULL DEFAULT 'other',
            slug TEXT,
            relative_path TEXT,
            title TEXT,
            content_hash TEXT,
            sitemap_lastmod TEXT,
            status TEXT NOT NULL DEFAULT 'new',
            exported_at TEXT,
            first_downloaded_at TEXT,
            needs_reindex INTEGER NOT NULL DEFAULT 0,
            change_reason TEXT NOT NULL DEFAULT '',
            rag_indexed_at TEXT,
            error TEXT,
            updated_at TEXT NOT NULL,
            UNIQUE(project_slug, url)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_ke_pages_project ON knowledge_export_pages(project_slug)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_ke_pages_status ON knowledge_export_pages(project_slug, status)"
    )
    ke_cols = _table_columns(conn, "knowledge_export_pages")
    if _table_exists(conn, "knowledge_export_pages"):
        if "needs_reindex" not in ke_cols:
            conn.execute(
                "ALTER TABLE knowledge_export_pages ADD COLUMN needs_reindex INTEGER NOT NULL DEFAULT 0"
            )
        if "change_reason" not in ke_cols:
            conn.execute(
                "ALTER TABLE knowledge_export_pages ADD COLUMN change_reason TEXT NOT NULL DEFAULT ''"
            )
        if "rag_indexed_at" not in ke_cols:
            conn.execute(
                "ALTER TABLE knowledge_export_pages ADD COLUMN rag_indexed_at TEXT"
            )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_ke_pages_reindex "
        "ON knowledge_export_pages(project_slug, needs_reindex)"
    )

    # Migrate legacy Kanban statuses (5 columns → 3 columns).
    if _table_exists(conn, "calendar_items"):
        status_map = (
            ("planned", "pending"),
            ("writing", "in_progress"),
            ("review", "in_progress"),
            ("scheduled", "in_progress"),
            ("published", "done"),
        )
        for old_status, new_status in status_map:
            conn.execute(
                "UPDATE calendar_items SET status = ? WHERE status = ?",
                (new_status, old_status),
            )


def _configure_connection(conn: sqlite3.Connection) -> None:
    """Per-connection pragmas for concurrent FastAPI workers."""
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """
    Open SQLite connection with row factory.

    Output:
        sqlite3.Connection with WAL mode and migrations applied.
    """
    global _initialized, _schema_migrated
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    with _lock:
        if not _initialized:
            conn.executescript(SCHEMA_SQL)
            _initialized = True
        if not _schema_migrated:
            _migrate_schema(conn)
            conn.commit()
            _schema_migrated = True
    _configure_connection(conn)
    return conn


def reset_init_flag() -> None:
    """Reset module init flag (tests only)."""
    global _initialized, _schema_migrated
    _initialized = False
    _schema_migrated = False
