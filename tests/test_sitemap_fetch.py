"""Tests for web sitemap fetch helper."""

from web.app.services.sitemap_fetch import normalize_sitemap_url


def test_normalize_sitemap_url_adds_https():
    """Bare domains should get https scheme."""
    assert normalize_sitemap_url("example.com/sitemap.xml") == "https://example.com/sitemap.xml"


def test_normalize_sitemap_url_strips_whitespace():
    """Whitespace around URL should be trimmed."""
    assert normalize_sitemap_url("  https://example.com/sitemap.xml  ") == "https://example.com/sitemap.xml"
