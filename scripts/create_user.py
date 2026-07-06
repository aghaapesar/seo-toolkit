"""Create or list toolkit users (username/password)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from web.app.services.auth_service import create_user, grant_project_access, list_users  # noqa: E402


def main() -> None:
    """CLI entry: create user or list users."""
    parser = argparse.ArgumentParser(description="Seo Toolkit user management")
    sub = parser.add_subparsers(dest="cmd", required=True)

    create_p = sub.add_parser("create", help="Create a user")
    create_p.add_argument("username")
    create_p.add_argument("password")
    create_p.add_argument("--display-name", default="")
    create_p.add_argument("--admin", action="store_true")
    create_p.add_argument("--project", action="append", default=[], help="Grant project slug access")

    sub.add_parser("list", help="List users")

    args = parser.parse_args()
    if args.cmd == "create":
        user = create_user(
            args.username,
            args.password,
            display_name=args.display_name,
            is_admin=args.admin,
        )
        for slug in args.project:
            grant_project_access(user.id, slug)
        print(f"Created user id={user.id} username={user.username} admin={user.is_admin}")
    elif args.cmd == "list":
        for row in list_users():
            print(f"{row['id']}\t{row['username']}\tadmin={row['is_admin']}\t{row['created_at']}")


if __name__ == "__main__":
    main()
