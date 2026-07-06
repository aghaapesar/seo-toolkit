"""
Username/password authentication with PBKDF2 hashing.

Input:
    Login credentials, user creation requests.

Output:
    User records and session user_id for Starlette sessions.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from web.app.services.database import get_connection

# PBKDF2 iterations for password hashing.
_PBKDF2_ROUNDS = 120_000


@dataclass
class User:
    """Authenticated user record."""

    id: int
    username: str
    display_name: str
    is_admin: bool

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for API responses (no secrets)."""
        return {
            "id": self.id,
            "username": self.username,
            "display_name": self.display_name or self.username,
            "is_admin": self.is_admin,
        }


def hash_password(password: str) -> str:
    """
    Hash password with random salt.

    Input:
        password: Plain text password.

    Output:
        Stored hash string `pbkdf2_sha256$salt$hex`.
    """
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        _PBKDF2_ROUNDS,
    )
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Verify plain password against stored PBKDF2 hash."""
    try:
        scheme, salt, hex_digest = stored.split("$", 2)
        if scheme != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            _PBKDF2_ROUNDS,
        )
        return secrets.compare_digest(digest.hex(), hex_digest)
    except (ValueError, AttributeError):
        return False


def create_user(
    username: str,
    password: str,
    *,
    display_name: str = "",
    is_admin: bool = False,
) -> User:
    """
    Register a new user.

    Input:
        username: Unique login name.
        password: Plain password (min 6 chars).

    Output:
        Created User.
    """
    username = username.strip().lower()
    if len(username) < 2:
        raise ValueError("Username too short")
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters")

    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO users (username, password_hash, display_name, is_admin)
            VALUES (?, ?, ?, ?)
            """,
            (username, hash_password(password), display_name or username, int(is_admin)),
        )
        conn.commit()
        return User(
            id=int(cur.lastrowid),
            username=username,
            display_name=display_name or username,
            is_admin=is_admin,
        )
    except Exception as exc:
        if "UNIQUE" in str(exc):
            raise ValueError("Username already exists") from exc
        raise


def authenticate(username: str, password: str) -> Optional[User]:
    """
    Validate credentials.

    Output:
        User if valid, else None.
    """
    username = username.strip().lower()
    conn = get_connection()
    row = conn.execute(
        "SELECT id, username, password_hash, display_name, is_admin FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    if not row or not verify_password(password, row["password_hash"]):
        return None
    return User(
        id=row["id"],
        username=row["username"],
        display_name=row["display_name"] or row["username"],
        is_admin=bool(row["is_admin"]),
    )


def get_user_by_id(user_id: int) -> Optional[User]:
    """Load user by primary key."""
    conn = get_connection()
    row = conn.execute(
        "SELECT id, username, display_name, is_admin FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    if not row:
        return None
    return User(
        id=row["id"],
        username=row["username"],
        display_name=row["display_name"] or row["username"],
        is_admin=bool(row["is_admin"]),
    )


def user_can_access_project(user_id: int, project_slug: str, *, is_admin: bool) -> bool:
    """Check project membership or admin override."""
    if is_admin or not project_slug:
        return True
    conn = get_connection()
    row = conn.execute(
        "SELECT 1 FROM project_members WHERE user_id = ? AND project_slug = ?",
        (user_id, project_slug),
    ).fetchone()
    return row is not None


def grant_project_access(user_id: int, project_slug: str, role: str = "editor") -> None:
    """Assign user to a project."""
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO project_members (user_id, project_slug, role)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, project_slug) DO UPDATE SET role = excluded.role
        """,
        (user_id, project_slug, role),
    )
    conn.commit()


def list_project_members(project_slug: str) -> List[Dict[str, Any]]:
    """
    List users assigned to a project.

    Output:
        Member dicts with id, username, display_name, role.
    """
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT u.id, u.username, u.display_name, pm.role
        FROM project_members pm
        JOIN users u ON u.id = pm.user_id
        WHERE pm.project_slug = ?
        ORDER BY COALESCE(u.display_name, u.username), u.username
        """,
        (project_slug,),
    ).fetchall()
    return [dict(r) for r in rows]


def list_users() -> List[Dict[str, Any]]:
    """List users for admin UI."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, username, display_name, is_admin, created_at FROM users ORDER BY username"
    ).fetchall()
    return [dict(r) for r in rows]
