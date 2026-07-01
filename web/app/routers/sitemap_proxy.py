"""Sitemap proxy for browser clients blocked by CORS on sub-sitemaps."""

from urllib.parse import unquote

from fastapi import APIRouter, HTTPException, Query

from src.services.http_client import fetch_url
from web.app.services.sitemap_fetch import normalize_sitemap_url

router = APIRouter(prefix="/api/v1/sitemap", tags=["sitemap"])


@router.get("/proxy")
def proxy_sitemap(url: str = Query(..., min_length=8)):
    """
    Fetch sitemap XML server-side when the browser cannot (CORS / mixed content).

    Input:
        url: Absolute sitemap or sub-sitemap URL.

    Output:
        JSON with raw XML text in `content`.
    """
    normalized = normalize_sitemap_url(unquote(url))
    if not normalized:
        raise HTTPException(status_code=400, detail="Invalid sitemap URL")

    content, fetch_error = fetch_url(normalized, timeout=60, max_retries=5)
    if not content:
        raise HTTPException(
            status_code=502,
            detail=fetch_error or "Failed to download sitemap from server",
        )

    # Decode bytes to text for browser XML parsing.
    text = content.decode("utf-8", errors="replace")
    return {"url": normalized, "content": text, "bytes": len(content)}
