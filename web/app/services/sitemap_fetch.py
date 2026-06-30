"""Non-interactive sitemap URL fetching for web API."""

from typing import List, Optional, Tuple

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

    manager = SitemapManager()
    content = manager._download_with_retry(
        url,
        max_retries=max_retries,
        timeout=timeout,
        silent=True,
    )
    if not content:
        detail = manager.last_download_error or "Failed to download sitemap"
        return [], f"Failed to download sitemap: {detail}"

    urls, sub_sitemaps = manager._parse_sitemap_content(content)
    if sub_sitemaps:
        all_urls: List[str] = []
        failed_subs: List[str] = []
        for sub_url in sub_sitemaps:
            sub_content = manager._download_with_retry(
                sub_url,
                max_retries=max_retries,
                timeout=timeout,
                silent=True,
            )
            if not sub_content:
                failed_subs.append(sub_url)
                continue
            sub_urls, nested = manager._parse_sitemap_content(sub_content)
            if nested:
                # Nested index — fetch each child (common on large WordPress sites)
                for nested_url in nested:
                    nested_content = manager._download_with_retry(
                        nested_url,
                        max_retries=max_retries,
                        timeout=timeout,
                        silent=True,
                    )
                    if nested_content:
                        nested_urls, _ = manager._parse_sitemap_content(nested_content)
                        all_urls.extend(nested_urls)
            else:
                all_urls.extend(sub_urls)

        if not all_urls:
            if failed_subs:
                return [], (
                    f"Downloaded sitemap index but failed sub-sitemaps "
                    f"({len(failed_subs)}/{len(sub_sitemaps)})"
                )
            return [], "No URLs found in sitemap index"

        # Deduplicate while preserving order
        seen = set()
        unique: List[str] = []
        for page_url in all_urls:
            if page_url not in seen:
                seen.add(page_url)
                unique.append(page_url)
        return unique, None

    if not urls:
        return [], "No URLs found in sitemap XML"

    return urls, None
