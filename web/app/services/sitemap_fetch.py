"""Non-interactive sitemap URL fetching for web API."""

from typing import List

from src.sitemap_manager import SitemapManager


def fetch_all_sitemap_urls(sitemap_url: str, max_retries: int = 3) -> List[str]:
    """
    Download sitemap and return all URLs without CLI prompts.

    Input:
        sitemap_url: Root sitemap or sitemap index URL.

    Output:
        List of page URLs from sitemap(s).
    """
    manager = SitemapManager()
    content = manager._download_with_retry(sitemap_url, max_retries=max_retries)
    if not content:
        return []

    urls, sub_sitemaps = manager._parse_sitemap_content(content)
    if sub_sitemaps:
        all_urls: List[str] = []
        for sub_url in sub_sitemaps:
            sub_content = manager._download_with_retry(sub_url, max_retries=max_retries)
            if not sub_content:
                continue
            sub_urls, _ = manager._parse_sitemap_content(sub_content)
            all_urls.extend(sub_urls)
        return all_urls

    return urls
