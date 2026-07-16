"""
Parse sitemap XML for URL → lastmod mapping.

Input:
    Root sitemap URL or raw XML bytes.

Output:
    Dict mapping page URL to lastmod ISO string (when present).
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin

from lxml import etree

from src.services.http_client import fetch_url
from src.sitemap_manager import SitemapManager

logger = logging.getLogger(__name__)

_NS = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def _parse_url_entries(content: bytes) -> Tuple[List[Tuple[str, Optional[str]]], List[str]]:
    """
    Parse one sitemap file for (loc, lastmod) pairs and sub-sitemap locs.

    Output:
        Tuple of url entries and sub-sitemap URLs.
    """
    try:
        root = etree.fromstring(content)
    except etree.XMLSyntaxError as exc:
        logger.warning("Sitemap XML parse error: %s", exc)
        return [], []

    entries: List[Tuple[str, Optional[str]]] = []
    sub_sitemaps: List[str] = []

    url_nodes = root.xpath("//ns:url", namespaces=_NS)
    if not url_nodes:
        url_nodes = root.xpath('//*[local-name()="url"]')

    for node in url_nodes:
        loc = _first_text(node, "loc")
        lastmod = _first_text(node, "lastmod")
        if loc:
            entries.append((loc.strip(), (lastmod or "").strip() or None))

    sm_nodes = root.xpath("//ns:sitemap/ns:loc/text()", namespaces=_NS)
    if not sm_nodes:
        sm_nodes = root.xpath('//*[local-name()="sitemap"]/*[local-name()="loc"]/text()')
    sub_sitemaps = [str(x).strip() for x in sm_nodes if str(x).strip()]

    return entries, sub_sitemaps


def _first_text(parent, local_name: str) -> str:
    """Read first child text by local name."""
    nodes = parent.xpath(f'ns:{local_name}/text()', namespaces=_NS)
    if not nodes:
        nodes = parent.xpath(f'*[local-name()="{local_name}"]/text()')
    return str(nodes[0]).strip() if nodes else ""


def fetch_url_lastmod_map(
    sitemap_url: str,
    *,
    timeout: int = 45,
    max_retries: int = 3,
) -> Dict[str, str]:
    """
    Recursively fetch sitemap tree and build URL → lastmod map.

    Output:
        Dict of page URL to lastmod string (may be empty for some URLs).
    """
    root = (sitemap_url or "").strip()
    if not root:
        return {}

    result: Dict[str, str] = {}
    visited: set[str] = set()
    queue: List[str] = [root]

    while queue:
        sm_url = queue.pop(0)
        if sm_url in visited:
            continue
        visited.add(sm_url)

        content, error = fetch_url(sm_url, timeout=timeout, max_retries=max_retries)
        if not content:
            logger.warning("Sitemap fetch failed %s: %s", sm_url, error)
            continue

        entries, subs = _parse_url_entries(content)
        if entries:
            for loc, lastmod in entries:
                if lastmod:
                    result[loc] = lastmod
                else:
                    result.setdefault(loc, "")
        elif subs:
            for sub in subs:
                abs_sub = urljoin(sm_url, sub)
                if abs_sub not in visited:
                    queue.append(abs_sub)
        else:
            # Fallback: leaf URLs without lastmod via shared parser
            mgr = SitemapManager()
            urls, more_subs = mgr._parse_sitemap_content(content)
            for u in urls:
                result.setdefault(u, "")
            for sub in more_subs:
                abs_sub = urljoin(sm_url, sub)
                if abs_sub not in visited:
                    queue.append(abs_sub)

    return result
