"""Read-only dashboard summary API for the home page."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends

from web.app.deps.auth import get_optional_user
from web.app.services.auth_service import User
from web.app.services.dashboard_service import get_dashboard_summary

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/summary")
def dashboard_summary(
    project_slug: str = "",
    user: Optional[User] = Depends(get_optional_user),
):
    """
    Aggregate KPIs and chart data for the dashboard.

    Input:
        project_slug: Active project scope (optional).

    Output:
        Read-only summary — does not mutate any store.
    """
    uid = user.id if user else None
    is_admin = bool(user and user.is_admin)
    return get_dashboard_summary(
        project_slug=project_slug.strip() or None,
        user_id=uid,
        is_admin=is_admin,
    )
