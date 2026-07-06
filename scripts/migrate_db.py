#!/usr/bin/env python3
"""
One-shot SQLite migration for calendar campaigns (v3.2).

Input:
    data/seo_toolkit.db (or --db path)

Output:
    Adds campaigns table + campaign_id columns if missing.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from web.app.services.database import DB_PATH, _migrate_schema, get_connection, reset_init_flag


def main() -> int:
    """Run migration and print column status."""
    parser = argparse.ArgumentParser(description="Migrate seo_toolkit SQLite schema")
    parser.add_argument("--db", type=Path, default=DB_PATH, help="Database file path")
    args = parser.parse_args()

    reset_init_flag()
    conn = get_connection(args.db)
    boards = conn.execute("PRAGMA table_info(calendar_boards)").fetchall()
    items = conn.execute("PRAGMA table_info(calendar_items)").fetchall()
    board_cols = [r[1] for r in boards]
    item_cols = [r[1] for r in items]
    print(f"DB: {args.db.resolve()}")
    print(f"calendar_boards columns: {', '.join(board_cols)}")
    print(f"calendar_items columns: {', '.join(item_cols)}")
    if "campaign_id" in board_cols and "campaign_id" in item_cols:
        print("OK — campaign_id present")
        return 0
    print("Running explicit migration…")
    _migrate_schema(conn)
    conn.commit()
    board_cols = [r[1] for r in conn.execute("PRAGMA table_info(calendar_boards)")]
    item_cols = [r[1] for r in conn.execute("PRAGMA table_info(calendar_items)")]
    print(f"After migrate — boards: {', '.join(board_cols)}")
    print(f"After migrate — items: {', '.join(item_cols)}")
    return 0 if "campaign_id" in board_cols else 1


if __name__ == "__main__":
    raise SystemExit(main())
