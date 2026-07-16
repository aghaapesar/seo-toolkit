"""Authentication API — login, logout, current user."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from web.app.services.auth_service import authenticate, get_user_by_id

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    """Username/password login body."""

    username: str = Field(..., min_length=2)
    password: str = Field(..., min_length=1)


@router.post("/login")
def login(payload: LoginRequest, request: Request):
    """
    Authenticate and store user_id in session.

    Output:
        User profile (no password).
    """
    user = authenticate(payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    request.session["user_id"] = user.id
    return {"user": user.to_dict()}


@router.post("/logout")
def logout(request: Request):
    """Clear session."""
    request.session.clear()
    return {"ok": True}


@router.get("/me")
def me(request: Request):
    """Return current session user or null."""
    user_id = request.session.get("user_id")
    if not user_id:
        return {"user": None}
    user = get_user_by_id(int(user_id))
    if not user:
        request.session.clear()
        return {"user": None}
    return {"user": user.to_dict()}
