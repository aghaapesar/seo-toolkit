"""Tests for sitemap fetch helpers."""

from web.app.services.sitemap_fetch import (
    collect_urls_from_bytes,
    normalize_sitemap_url,
)
from src.sitemap_manager import SitemapManager


SITEMAP_XML = b"""<?xml version='1.0' encoding='UTF-8'?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/a</loc></url>
  <url><loc>https://example.com/b</loc></url>
</urlset>
"""


def test_normalize_sitemap_url_adds_https():
    """Bare domains should get https scheme."""
    assert normalize_sitemap_url("example.com/sitemap.xml") == "https://example.com/sitemap.xml"


def test_collect_urls_from_bytes_parses_leaf_sitemap():
    """Uploaded leaf sitemap should return URLs without HTTP."""
    manager = SitemapManager(sitemap_dir="sitemaps")
    urls, err = collect_urls_from_bytes(
        SITEMAP_XML,
        manager,
        fetch_remote_children=False,
    )
    assert err is None
    assert urls == ["https://example.com/a", "https://example.com/b"]
