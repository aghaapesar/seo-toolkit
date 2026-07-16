"""Tests for URL-pattern sitemap segment analyzer."""

from src.knowledge_exporter.sitemap_analyzer import (
    build_pattern_segments,
    extract_url_pattern,
    group_urls_by_pattern,
    resolve_selected_urls,
    _majority_content_type,
)


def test_extract_url_pattern_listing():
    """Listing paths collapse slug segment to *."""
    assert extract_url_pattern("https://shop.example/product/game-a") == "/product/*"
    assert extract_url_pattern("https://shop.example/fa/blog/post-1") == "/blog/*"
    assert extract_url_pattern("https://shop.example/") == "/"


def test_extract_url_pattern_two_level():
    """Structural two-level paths keep both segments."""
    assert extract_url_pattern("https://shop.example/product-category/toys") == "/product-category/toys/"


def test_group_and_build_segments_with_samples():
    """Pattern groups produce segments with content type from samples."""
    urls = [
        "https://example.com/product/a",
        "https://example.com/product/b",
        "https://example.com/blog/x",
    ]
    grouped = group_urls_by_pattern(urls)
    assert "/product/*" in grouped
    assert "/blog/*" in grouped

    sample_results = {
        "/product/*": [
            {"url": urls[0], "status": "success", "content_type": "product", "title": "Game A"},
            {"url": urls[1], "status": "success", "content_type": "product", "title": "Game B"},
        ],
        "/blog/*": [
            {"url": urls[2], "status": "success", "content_type": "blog", "title": "Post X"},
        ],
    }
    segments, segment_urls = build_pattern_segments(grouped, sample_results)
    assert len(segments) == 2
    product_seg = next(s for s in segments if s["url_pattern"] == "/product/*")
    assert product_seg["content_type"] == "product"
    assert product_seg["sample_confidence"] == "2/2"

    analysis = {"all_urls": urls, "segment_urls": segment_urls}
    selected = resolve_selected_urls(analysis, [product_seg["id"]])
    assert len(selected) == 2


def test_majority_content_type_vote():
    """Majority vote picks dominant type from samples."""
    samples = [
        {"status": "success", "content_type": "product"},
        {"status": "success", "content_type": "product"},
        {"status": "success", "content_type": "other"},
    ]
    ctype, conf = _majority_content_type(samples)
    assert ctype == "product"
    assert conf == "2/3"
