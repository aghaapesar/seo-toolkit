"""Unit tests for SitemapManager XML parsing."""

from src.sitemap_manager import SitemapManager


def test_parse_sitemap_content_extracts_urls():
    """Parser should read URL entries from sitemap XML."""
    xml = b"""<?xml version='1.0' encoding='UTF-8'?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url><loc>https://example.com/a</loc></url>
      <url><loc>https://example.com/b</loc></url>
    </urlset>
    """
    manager = SitemapManager(sitemap_dir="sitemaps")
    urls, sub_sitemaps = manager._parse_sitemap_content(xml)

    assert urls == ["https://example.com/a", "https://example.com/b"]
    assert sub_sitemaps == []


def test_parse_sitemap_content_local_name_fallback():
    """Parser should work when xmlns differs from the standard sitemap schema."""
    xml = b"""<?xml version='1.0' encoding='UTF-8'?>
    <urlset xmlns="http://www.google.com/schemas/sitemap/0.84">
      <url><loc>https://example.com/x</loc></url>
    </urlset>
    """
    manager = SitemapManager(sitemap_dir="sitemaps")
    urls, sub_sitemaps = manager._parse_sitemap_content(xml)

    assert urls == ["https://example.com/x"]
    assert sub_sitemaps == []
