"""FastAPI dependencies for authentication."""

from __future__ import annotations

from fastapi import HTTPException, Request

from web.app.services.auth_service import User, get_user_by_id


def get_optional_user(request: Request) -> User | None:
    """Return logged-in user from session or None."""
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return get_user_by_id(int(user_id))


def require_user(request: Request) -> User:
    """Require authenticated session for API routes."""
    user = get_optional_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    return user
