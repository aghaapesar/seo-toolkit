"""Content calendar Kanban API."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from pydantic import BaseModel, Field

from web.app.deps.auth import require_user
from web.app.services.auth_service import User, list_project_members, user_can_access_project
from web.app.services.calendar_store import (
    KANBAN_STATUSES,
    create_campaign,
    delete_campaign,
    delete_item,
    get_board,
    get_board_by_job,
    get_campaign,
    get_campaign_board,
    get_item,
    get_item_project_slug,
    list_boards,
    list_campaigns,
    reorder_campaigns,
    update_item,
)

router = APIRouter(prefix="/api/v1/calendar", tags=["calendar"])


class ItemUpdateRequest(BaseModel):
    """PATCH body for a Kanban card."""

    status: Optional[str] = None
    notes: Optional[str] = None
    checklist: Optional[List[Dict[str, Any]]] = None
    campaign_id: Optional[str] = None
    h2_headings: Optional[str] = None
    assigned_user_id: Optional[int] = None


class CampaignCreateRequest(BaseModel):
    """POST body for a new campaign."""

    project_slug: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)


class CampaignReorderRequest(BaseModel):
    """PATCH body to reorder campaign tabs."""

    project_slug: str = Field(..., min_length=1)
    ordered_ids: List[str] = Field(..., min_length=1)


def _assert_project_access(user: User, project_slug: str) -> None:
    """Raise 403 when user cannot access project."""
    if project_slug and not user_can_access_project(user.id, project_slug, is_admin=user.is_admin):
        raise HTTPException(status_code=403, detail="No access to this project")


def _members_payload(project_slug: str, user: User) -> list:
    """Members for calendar card assignee dropdown."""
    members = list_project_members(project_slug)
    if not members:
        members = [
            {
                "id": user.id,
                "username": user.username,
                "display_name": user.display_name or user.username,
                "role": "editor",
            }
        ]
    return members


@router.get("/members")
def calendar_members(project_slug: str, user: User = Depends(require_user)):
    """List project members available for calendar card assignment."""
    slug = project_slug.strip()
    if not slug:
        raise HTTPException(status_code=400, detail="project_slug required")
    _assert_project_access(user, slug)
    return {"members": _members_payload(slug, user)}


@router.get("/statuses")
def kanban_statuses():
    """Return valid Kanban column keys."""
    return {"statuses": list(KANBAN_STATUSES)}


@router.get("/campaigns")
def campaigns_list(
    project_slug: str,
    user: User = Depends(require_user),
):
    """List campaigns for a project."""
    slug = project_slug.strip()
    if not slug:
        raise HTTPException(status_code=400, detail="project_slug required")
    _assert_project_access(user, slug)
    return {"campaigns": list_campaigns(slug)}


@router.post("/campaigns")
def campaign_create(payload: CampaignCreateRequest, user: User = Depends(require_user)):
    """Create a named campaign for a project."""
    slug = payload.project_slug.strip()
    _assert_project_access(user, slug)
    campaign = create_campaign(slug, payload.name.strip())
    return {"campaign": campaign}


@router.get("/campaigns/{campaign_id}/board")
def campaign_board(campaign_id: str, user: User = Depends(require_user)):
    """Load Kanban items for one campaign."""
    board = get_campaign_board(campaign_id)
    if not board:
        raise HTTPException(status_code=404, detail="Campaign not found")
    slug = board.get("project_slug") or ""
    if slug:
        _assert_project_access(user, slug)
    return board


@router.patch("/campaigns/reorder")
def campaigns_reorder(payload: CampaignReorderRequest, user: User = Depends(require_user)):
    """Reorder campaign tabs after drag-and-drop."""
    slug = payload.project_slug.strip()
    _assert_project_access(user, slug)
    campaigns = reorder_campaigns(slug, payload.ordered_ids)
    return {"campaigns": campaigns}


@router.delete("/campaigns/{campaign_id}")
def campaign_delete(campaign_id: str, user: User = Depends(require_user)):
    """Delete a campaign and all items inside it."""
    camp = get_campaign(campaign_id)
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found")
    slug = camp.get("project_slug") or ""
    if slug:
        _assert_project_access(user, slug)
    if not delete_campaign(campaign_id):
        raise HTTPException(status_code=404, detail="Campaign not found")
    return {"ok": True, "deleted_id": campaign_id}


@router.get("/boards")
def boards_list(
    project_slug: str = "",
    user: User = Depends(require_user),
):
    """List calendar boards (optionally per project)."""
    slug = project_slug.strip() or None
    if slug:
        _assert_project_access(user, slug)
    return {"boards": list_boards(slug)}


@router.get("/boards/{board_id}")
def board_detail(board_id: str, user: User = Depends(require_user)):
    """Load full board with items."""
    board = get_board(board_id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    slug = board.get("project_slug") or ""
    if slug:
        _assert_project_access(user, slug)
    return board


@router.get("/by-job/{job_id}")
def board_by_job(job_id: str, user: User = Depends(require_user)):
    """Resolve board created from a cluster job."""
    board = get_board_by_job(job_id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found for this job")
    slug = board.get("project_slug") or ""
    if slug:
        _assert_project_access(user, slug)
    return board


@router.patch("/items/{item_id}")
def patch_item(
    item_id: str,
    payload: ItemUpdateRequest,
    user: User = Depends(require_user),
):
    """Update card status, notes, checklist, campaign, or assignee."""
    fields = payload.model_dump(exclude_unset=True)
    try:
        item = update_item(item_id, updated_by=user.id, **fields)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"item": item}


@router.delete("/items/{item_id}")
def remove_item(item_id: str, user: User = Depends(require_user)):
    """Permanently delete a Kanban card."""
    slug = get_item_project_slug(item_id)
    if slug:
        _assert_project_access(user, slug)
    if not delete_item(item_id):
        raise HTTPException(status_code=404, detail="Item not found")
    return {"ok": True, "deleted_id": item_id}


@router.post("/items/{item_id}/link-suggestions")
def item_link_suggestions(
    item_id: str,
    project_slug: str = Form(""),
    model_name: str = Form(""),
    use_ai: bool = Form(True),
    user: User = Depends(require_user),
):
    """
    Suggest internal links (products/categories) for a calendar card.

    Input:
        project_slug: Required — site index scope.
        model_name: Optional AI model for refinement.
        use_ai: If False, rule-based only.

    Output:
        suggestions list; saves to item.suggested_links.
    """
    from src.ai_errors import credit_exhausted_message
    from src.ai_model_manager import AIModelManager
    from src.link_suggestion_ai import suggest_links_for_item
    from web.app.services.site_index_store import get_index_stats

    item = get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    slug = project_slug.strip() or get_item_project_slug(item_id) or ""
    if not slug:
        raise HTTPException(status_code=400, detail="project_slug required")
    if not user_can_access_project(user.id, slug, is_admin=user.is_admin):
        raise HTTPException(status_code=403, detail="No access to this project")

    stats = get_index_stats(slug)
    if (stats.get("total_pages") or 0) < 1:
        raise HTTPException(
            status_code=400,
            detail="Site index empty — run Site Index tool first",
        )

    model = None
    if use_ai:
        manager = AIModelManager("config.yaml")
        model = manager.get_model(model_name.strip() or None) or manager.get_default_model()
        if not model:
            use_ai = False

    result = suggest_links_for_item(item, slug, model, use_ai=use_ai)
    update_item(
        item_id,
        suggested_links=result.get("suggestions") or [],
        updated_by=user.id,
    )

    response = {
        "suggestions": result.get("suggestions") or [],
        "used_ai": result.get("used_ai", False),
        "credit_exhausted": result.get("credit_exhausted", False),
    }
    if result.get("credit_exhausted"):
        response["credit_message"] = credit_exhausted_message("fa")
        response["notify_recharge"] = True
    return response


@router.post("/items/{item_id}/h2-rewrite")
def rewrite_item_h2(
    item_id: str,
    heading_index: int = Form(...),
    use_ai: bool = Form(True),
    model_name: str = Form(""),
    user: User = Depends(require_user),
):
    """
    Rewrite one H2 heading on a Kanban card (AI or rule-based).

    Input:
        heading_index: Zero-based index in h2_headings list.
        use_ai: Use LLM when configured.

    Output:
        Updated item with new heading at index.
    """
    from src.ai_errors import credit_exhausted_message
    from src.ai_model_manager import AIModelManager
    from src.h2_heading_ai import parse_h2_headings, rewrite_h2_at_index, serialize_h2_headings

    item = get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    slug = get_item_project_slug(item_id) or ""
    if slug:
        _assert_project_access(user, slug)

    headings = parse_h2_headings(item.get("h2_headings"))
    if heading_index < 0 or heading_index >= len(headings):
        raise HTTPException(status_code=400, detail="Invalid heading index")

    model = None
    if use_ai:
        manager = AIModelManager("config.yaml")
        model = manager.get_model(model_name.strip() or None) or manager.get_default_model()
        if not model:
            use_ai = False

    credit_exhausted = False
    credit_message = ""
    try:
        new_heading = rewrite_h2_at_index(
            item, heading_index, model=model, use_ai=use_ai
        )
    except RuntimeError as exc:
        if str(exc) == "credit_exhausted":
            credit_exhausted = True
            credit_message = credit_exhausted_message("fa")
            new_heading = rewrite_h2_at_index(item, heading_index, model=None, use_ai=False)
        else:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    headings[heading_index] = new_heading
    updated = update_item(
        item_id,
        h2_headings=serialize_h2_headings(headings),
        updated_by=user.id,
    )
    return {
        "item": updated,
        "heading": new_heading,
        "heading_index": heading_index,
        "used_ai": use_ai and model is not None and not credit_exhausted,
        "credit_exhausted": credit_exhausted,
        "credit_message": credit_message,
    }
