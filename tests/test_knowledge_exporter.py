"""Tests for knowledge_exporter module."""

import json
import tempfile
from pathlib import Path

import pytest

from src.knowledge_exporter.config import KnowledgeExporterConfig
from src.knowledge_exporter.content_extractor import (
    detect_boilerplate_lines,
    extract_page_content,
    strip_boilerplate,
)
from src.knowledge_exporter.part_writer import DOCUMENT_SEPARATOR, PageDocument, PartWriter


SAMPLE_HTML = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
  <title>عنوان تست</title>
  <meta name="description" content="توضیحات متا">
</head>
<body>
  <header><nav>Menu item repeated</nav></header>
  <main>
    <h1>عنوان تست</h1>
    <p>متن اصلی صفحه با محتوای فارسی.</p>
    <h2>زیرعنوان</h2>
    <ul><li>مورد اول</li><li>مورد دوم</li></ul>
    <table><tr><th>ستون</th><th>مقدار</th></tr>
    <tr><td>الف</td><td>1</td></tr></table>
    <p><a href="/page">Link text</a></p>
  </main>
  <footer>Footer repeated line here for boilerplate</footer>
</body>
</html>""".encode("utf-8")


def test_config_url_filters():
    """Include/exclude regex filters URLs correctly."""
    cfg = KnowledgeExporterConfig(
        output_dir=Path("/tmp/out"),
        include_pattern=r"/blog/",
        exclude_pattern=r"/tag/",
    )
    assert cfg.url_allowed("https://example.com/blog/post")
    assert not cfg.url_allowed("https://example.com/product/x")
    assert not cfg.url_allowed("https://example.com/blog/tag/foo")


def test_extract_page_content_persian():
    """Extract title, description, lang, and markdown from Persian HTML."""
    page = extract_page_content(SAMPLE_HTML, "https://example.com/test")
    assert page.title
    assert page.description
    assert page.lang in ("fa", "fa-IR", "")
    assert len(page.markdown) >= 50
    assert "متن" in page.markdown or "عنوان" in page.markdown


def test_boilerplate_detection_and_removal():
    """Repeated lines across docs are detected and stripped."""
    docs = [
        "Line A\nFooter repeated line here for boilerplate\nContent one",
        "Line B\nFooter repeated line here for boilerplate\nContent two",
        "Line C\nFooter repeated line here for boilerplate\nContent three",
    ]
    boilerplate = detect_boilerplate_lines(docs, min_ratio=0.5)
    assert "Footer repeated line here for boilerplate" in boilerplate
    cleaned = strip_boilerplate(docs[0], boilerplate)
    assert "Footer repeated line here for boilerplate" not in cleaned
    assert "Content one" in cleaned


def test_part_writer_splits_and_index():
    """Part writer creates files, separators, and index.json."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        writer = PartWriter(output_dir=out, max_part_bytes=800, max_pages_per_part=2)
        docs = [
            PageDocument(
                url=f"https://example.com/p{i}",
                title=f"Page {i}",
                description="desc",
                lang="fa",
                markdown_body=f"Body content for page {i} " * 5,
                crawled_at="2026-07-05T12:00:00+00:00",
                status="success",
            )
            for i in range(3)
        ]
        parts = writer.write_all(docs)
        assert len(parts) >= 2
        part1 = (out / parts[0]).read_text(encoding="utf-8")
        assert "url: https://example.com/p0" in part1
        assert DOCUMENT_SEPARATOR in (out / parts[1]).read_text(encoding="utf-8") or len(parts) == 2

        index = json.loads((out / "index.json").read_text(encoding="utf-8"))
        assert index["total_pages"] == 3
        assert len(index["pages"]) == 3
        assert index["pages"][0]["status"] == "success"


def test_url_to_slug_and_noindex():
    """Slug generation and noindex detection."""
    from src.knowledge_exporter.page_meta import detect_noindex, url_to_slug

    assert url_to_slug("https://shop.example.com/product/cool-widget/")
    noindex_html = b'<html><head><meta name="robots" content="noindex,nofollow"></head></html>'
    assert detect_noindex(noindex_html) is True
    assert detect_noindex(SAMPLE_HTML) is False


def test_rag_writer_per_url_files():
    """RagWriter writes pages/{type}/{slug}.md with standard url+title frontmatter."""
    from src.knowledge_exporter.rag_writer import RagPageDocument, RagWriter

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        writer = RagWriter(output_dir=out, write_parts=False)
        doc = RagPageDocument(
            url="https://example.com/product/foo",
            title="Foo Product",
            description="A product",
            lang="fa",
            markdown_body="# Foo Product\n\nBody text here.",
            crawled_at="2026-07-05T12:00:00+00:00",
            status="success",
            page_type="product",
            slug="foo",
            sitemap_lastmod="2026-01-01",
            content_hash="abc123",
        )
        result = writer.write_all([doc])
        assert len(result["written_paths"]) == 1
        path = out / result["written_paths"][0]
        text = path.read_text(encoding="utf-8")
        # Official RAG standard §2 / §7: only url + title in frontmatter
        assert text.startswith("---\n")
        assert 'url: https://example.com/product/foo' in text
        assert 'title: "Foo Product"' in text
        assert "page_type:" not in text.split("---", 2)[1]
        assert "content_hash:" not in text.split("---", 2)[1]
        assert "# Foo Product" in text
        index = json.loads((out / "index.json").read_text(encoding="utf-8"))
        assert index["format"] == "rag_per_url"


def test_cleanup_patterns_strip_site_chrome():
    """Standard §6 cleanup patterns remove Sargarmia-style boilerplate."""
    from src.knowledge_exporter.rag_ai import apply_cleanup_patterns

    raw = (
        "متن اصلی محصول اینجا است.\n"
        "از 12 رای\n"
        "برچسبها : بازی فکری, کارتی\n"
        "بخشها : رومیزی\n"
    )
    cleaned = apply_cleanup_patterns(raw)
    assert "متن اصلی محصول" in cleaned
    assert "از 12 رای" not in cleaned
    assert "برچسبها" not in cleaned


def test_extract_foreign_name_from_title():
    """Latin/foreign name is pulled from Persian product titles."""
    from src.knowledge_exporter.rag_ai import extract_foreign_name

    assert "Jaliz" in extract_foreign_name("بازی فکری جالیز - Jaliz Board Game")
    assert extract_foreign_name("فقط فارسی") == ""


def test_part_writer_keeps_oversized_doc_intact():
    """A single large product document is never split across part files."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        writer = PartWriter(output_dir=out, max_part_bytes=200, max_pages_per_part=50)
        big = "متن محصول کامل " * 80
        docs = [
            PageDocument(
                url="https://example.com/product/big",
                title="محصول بزرگ",
                description="",
                lang="fa",
                markdown_body=big,
                crawled_at="2026-07-22T12:00:00+00:00",
                status="success",
            )
        ]
        parts = writer.write_all(docs)
        assert len(parts) == 1
        content = (out / parts[0]).read_text(encoding="utf-8")
        assert "url: https://example.com/product/big" in content
        assert big[:40] in content
