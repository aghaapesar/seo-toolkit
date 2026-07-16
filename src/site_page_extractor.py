"""
Full site page extraction — metadata, body, products (JSON-LD).

Input:
    Page URL.

Output:
    Structured dict for site index storage.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import unquote, urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

_PRODUCT_PATH_HINTS = ("/product/", "/products/", "/محصول/", "/p/")
_CATEGORY_PATH_HINTS = ("/category/", "/categories/", "/shop/", "/دسته/", "/product-category/")
_BLOG_PATH_HINTS = ("/blog/", "/article/", "/post/", "/وبلاگ/", "/مقاله/")


def _decode_url(url: str) -> str:
    """Decode Persian URL path for fetching."""
    try:
        parsed = urlparse(url)
        path = unquote(parsed.path, encoding="utf-8")
        query = unquote(parsed.query, encoding="utf-8") if parsed.query else ""
        out = f"{parsed.scheme}://{parsed.netloc}{path}"
        if query:
            out += f"?{query}"
        return out
    except Exception:
        return url


def _parse_json_ld_blocks(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Extract all JSON-LD objects from a page."""
    items: List[Dict[str, Any]] = []
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = (tag.string or tag.get_text() or "").strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(data, list):
            items.extend(x for x in data if isinstance(x, dict))
        elif isinstance(data, dict):
            if "@graph" in data and isinstance(data["@graph"], list):
                items.extend(x for x in data["@graph"] if isinstance(x, dict))
            else:
                items.append(data)
    return items


def _ld_type(entry: Dict[str, Any]) -> str:
    """Normalize schema.org @type."""
    t = entry.get("@type") or ""
    if isinstance(t, list):
        return str(t[0]).lower() if t else ""
    return str(t).lower()


def _extract_product_from_ld(items: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Pull product fields from JSON-LD Product entries.

    Output:
        product_name, product_price, product_sku, categories (pipe-separated).
    """
    out = {"product_name": "", "product_price": "", "product_sku": "", "categories": ""}
    for entry in items:
        t = _ld_type(entry)
        if "product" not in t:
            continue
        out["product_name"] = str(entry.get("name") or out["product_name"] or "")
        offers = entry.get("offers")
        if isinstance(offers, dict):
            out["product_price"] = str(offers.get("price") or offers.get("lowPrice") or "")
        elif isinstance(offers, list) and offers:
            out["product_price"] = str(offers[0].get("price") or "")
        out["product_sku"] = str(entry.get("sku") or entry.get("mpn") or "")
        cat = entry.get("category")
        if isinstance(cat, str):
            out["categories"] = cat
        elif isinstance(cat, list):
            out["categories"] = " | ".join(str(c) for c in cat)
        break
    return out


def _detect_page_type(url: str, ld_items: List[Dict[str, Any]]) -> str:
    """Classify page as product, category, blog, or other."""
    for entry in ld_items:
        t = _ld_type(entry)
        if "product" in t:
            return "product"
        if "collectionpage" in t or "itemlist" in t:
            return "category"
        if "article" in t or "blogposting" in t:
            return "blog"
    path = urlparse(url).path.lower()
    for hint in _PRODUCT_PATH_HINTS:
        if hint in path:
            return "product"
    for hint in _CATEGORY_PATH_HINTS:
        if hint in path:
            return "category"
    for hint in _BLOG_PATH_HINTS:
        if hint in path:
            return "blog"
    return "other"


def _extract_body_text(soup: BeautifulSoup) -> str:
    """
    Extract main readable text from common CMS containers.

    Output:
        Plain text body (truncated in storage layer if needed).
    """
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()
    main = (
        soup.find("article")
        or soup.find("main")
        or soup.find(class_=re.compile(r"product|entry-content|post-content|content-area", re.I))
        or soup.find("div", id=re.compile(r"content|main", re.I))
    )
    root = main or soup.body or soup
    text = root.get_text(separator=" ", strip=True) if root else ""
    return re.sub(r"\s+", " ", text).strip()


def _extract_internal_links(soup: BeautifulSoup, base_url: str) -> List[str]:
    """Collect same-host anchor hrefs."""
    host = urlparse(base_url).netloc
    links: List[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#") or href.startswith("mailto:"):
            continue
        if href.startswith("/"):
            parsed = urlparse(base_url)
            href = f"{parsed.scheme}://{parsed.netloc}{href}"
        if urlparse(href).netloc == host:
            links.append(href)
    return list(dict.fromkeys(links))[:80]


def scrape_site_page(url: str, *, timeout: int = 15) -> Dict[str, Any]:
    """
    Scrape full page data for site index.

    Input:
        url: Target page URL.

    Output:
        Dict with metadata, body, product fields, page_type, status.
    """
    decoded = _decode_url(url)
    result: Dict[str, Any] = {
        "url": decoded,
        "original_url": url,
        "status": "pending",
        "title": "",
        "meta_description": "",
        "h1": "",
        "canonical_url": "",
        "body_text": "",
        "body_excerpt": "",
        "page_type": "other",
        "product_name": "",
        "product_price": "",
        "product_sku": "",
        "categories": "",
        "json_ld": [],
        "internal_links": [],
        "content_hash": "",
        "error": "",
    }

    try:
        response = requests.get(decoded, headers=_HEADERS, timeout=timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "lxml")

        title_tag = soup.find("title")
        if title_tag:
            result["title"] = title_tag.get_text().strip()
        meta = soup.find("meta", attrs={"name": "description"})
        if meta and meta.get("content"):
            result["meta_description"] = meta["content"].strip()
        h1 = soup.find("h1")
        if h1:
            result["h1"] = h1.get_text().strip()
        canonical = soup.find("link", attrs={"rel": "canonical"})
        if canonical and canonical.get("href"):
            result["canonical_url"] = canonical["href"]

        ld_items = _parse_json_ld_blocks(soup)
        result["json_ld"] = ld_items[:20]
        product_fields = _extract_product_from_ld(ld_items)
        result.update(product_fields)
        result["page_type"] = _detect_page_type(decoded, ld_items)

        body = _extract_body_text(soup)
        result["body_text"] = body[:50000]
        result["body_excerpt"] = body[:500]
        result["internal_links"] = _extract_internal_links(soup, decoded)
        if not result["product_name"] and result["page_type"] == "product":
            result["product_name"] = result["h1"] or result["title"]

        result["content_hash"] = hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]
        result["status"] = "success"
    except requests.Timeout:
        result["status"] = "timeout"
        result["error"] = f"Timeout after {timeout}s"
    except requests.RequestException as exc:
        result["status"] = "error"
        result["error"] = str(exc)[:300]
    except Exception as exc:
        result["status"] = "error"
        result["error"] = str(exc)[:300]
        logger.exception("scrape_site_page failed for %s", decoded)

    return result
