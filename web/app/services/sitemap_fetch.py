"""Non-interactive sitemap URL fetching for web API."""

from typing import List, Optional, Tuple

from src.services.http_client import fetch_url
from src.sitemap_manager import SitemapManager


def normalize_sitemap_url(sitemap_url: str) -> str:
    """
    Normalize user-provided sitemap URL.

    Input:
        sitemap_url: Raw URL from form or API.

    Output:
        Trimmed URL with scheme (defaults to https).
    """
    url = (sitemap_url or "").strip()
    if url and not url.startswith(("http://", "https://")):
        url = f"https://{url.lstrip('/')}"
    return url


def _dedupe_urls(urls: List[str]) -> List[str]:
    """Return unique URLs preserving first-seen order."""
    seen = set()
    unique: List[str] = []
    for page_url in urls:
        if page_url not in seen:
            seen.add(page_url)
            unique.append(page_url)
    return unique


def collect_urls_from_bytes(
    content: bytes,
    manager: SitemapManager,
    fetch_remote_children: bool = True,
    max_retries: int = 5,
    timeout: int = 45,
) -> Tuple[List[str], Optional[str]]:
    """
    Parse sitemap XML bytes and optionally fetch sub-sitemaps over HTTP.

    Input:
        content: Raw sitemap XML.
        manager: SitemapManager for parsing.
        fetch_remote_children: When True, download sub-sitemaps from index.

    Output:
        Tuple of (page URLs, error message).
    """
    urls, sub_sitemaps = manager._parse_sitemap_content(content)

    if not sub_sitemaps:
        if urls:
            return _dedupe_urls(urls), None
        return [], "No URLs found in sitemap XML"

    if not fetch_remote_children:
        return [], (
            f"Uploaded file is a sitemap index ({len(sub_sitemaps)} sub-sitemaps). "
            "Enable download or upload a leaf sitemap file."
        )

    all_urls: List[str] = []
    failed_subs: List[str] = []

    for sub_url in sub_sitemaps:
        sub_content, sub_error = fetch_url(
            sub_url, timeout=timeout, max_retries=max_retries
        )
        if not sub_content:
            failed_subs.append(sub_url)
            manager.last_download_error = sub_error
            continue

        sub_urls, nested = manager._parse_sitemap_content(sub_content)
        if nested:
            nested_urls, nested_error = collect_urls_from_bytes(
                sub_content,
                manager,
                fetch_remote_children=True,
                max_retries=max_retries,
                timeout=timeout,
            )
            if nested_error and not nested_urls:
                failed_subs.append(sub_url)
            else:
                all_urls.extend(nested_urls)
        else:
            all_urls.extend(sub_urls)

    if not all_urls:
        if failed_subs:
            detail = manager.last_download_error or "sub-sitemap download failed"
            return [], (
                f"Sitemap index found but could not download sub-sitemaps "
                f"({len(failed_subs)}/{len(sub_sitemaps)}). {detail}"
            )
        return [], "No URLs found in sitemap index"

    return _dedupe_urls(all_urls), None


def fetch_all_sitemap_urls(
    sitemap_url: str,
    max_retries: int = 5,
    timeout: int = 45,
) -> Tuple[List[str], Optional[str]]:
    """
    Download sitemap and return all URLs without CLI prompts.

    Input:
        sitemap_url: Root sitemap or sitemap index URL.
        max_retries: Download retry count per sitemap file.
        timeout: HTTP timeout in seconds.

    Output:
        Tuple of (url list, error message). error is None on success.
    """
    url = normalize_sitemap_url(sitemap_url)
    if not url:
        return [], "Sitemap URL is required"

    content, fetch_error = fetch_url(url, timeout=timeout, max_retries=max_retries)
    manager = SitemapManager()
    if not content:
        detail = fetch_error or manager.last_download_error or "Failed to download sitemap"
        return [], f"Failed to download sitemap: {detail}"

    return collect_urls_from_bytes(
        content,
        manager,
        fetch_remote_children=True,
        max_retries=max_retries,
        timeout=timeout,
    )


def parse_uploaded_sitemap_file(
    content: bytes,
    max_retries: int = 5,
    timeout: int = 45,
) -> Tuple[List[str], Optional[str]]:
    """
    Parse user-uploaded sitemap.xml (from browser Save As).

    Input:
        content: Uploaded file bytes.

    Output:
        Tuple of (page URLs, error message).
    """
    manager = SitemapManager()
    return collect_urls_from_bytes(
        content,
        manager,
        fetch_remote_children=True,
        max_retries=max_retries,
        timeout=timeout,
    )
