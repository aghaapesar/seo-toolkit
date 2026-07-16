"""
Main content extraction: HTML → Markdown for RAG.

Input:
    Raw HTML bytes and source URL.

Output:
    Extracted title, description, language, and Markdown body.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from html import unescape
from typing import List, Optional, Set
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, NavigableString, Tag

logger = logging.getLogger(__name__)

try:
    import trafilatura

    _HAS_TRAFILATURA = True
except ImportError:
    _HAS_TRAFILATURA = False

try:
    from readability import Document as ReadabilityDocument

    _HAS_READABILITY = True
except ImportError:
    _HAS_READABILITY = False


@dataclass
class ExtractedPage:
    """Structured extraction result for one page."""

    url: str
    title: str
    description: str
    lang: str
    markdown: str
    char_count: int


# Tags stripped before main-content heuristics
_NOISE_TAGS = {
    "script",
    "style",
    "noscript",
    "iframe",
    "svg",
    "header",
    "footer",
    "nav",
    "aside",
    "form",
    "button",
    "input",
    "select",
    "textarea",
}


def _detect_lang(soup: BeautifulSoup, text: str) -> str:
    """
    Detect page language from html lang or content heuristics.

    Output:
        BCP-47 language code or empty string.
    """
    html_tag = soup.find("html")
    if html_tag and html_tag.get("lang"):
        return str(html_tag.get("lang")).strip()
    # Persian Unicode block heuristic
    if re.search(r"[\u0600-\u06FF]", text):
        return "fa"
    return ""


def _meta_description(soup: BeautifulSoup) -> str:
    """Extract meta description from soup."""
    for tag in soup.find_all("meta"):
        name = (tag.get("name") or tag.get("property") or "").lower()
        if name in ("description", "og:description"):
            content = tag.get("content")
            if content:
                return str(content).strip()
    return ""


def _page_title(soup: BeautifulSoup) -> str:
    """Extract document title."""
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        return str(og["content"]).strip()
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(" ", strip=True)
    return ""


def _strip_noise(root: Tag) -> None:
    """Remove boilerplate elements from a BeautifulSoup subtree."""
    for tag_name in _NOISE_TAGS:
        for node in root.find_all(tag_name):
            node.decompose()
    for node in root.find_all(class_=re.compile(r"(cookie|banner|sidebar|menu|nav|footer|header|comment)", re.I)):
        node.decompose()
    for node in root.find_all(id=re.compile(r"(cookie|banner|sidebar|menu|nav|footer|header|comment)", re.I)):
        node.decompose()


def _pick_main_node(soup: BeautifulSoup) -> Tag:
    """
    Heuristic main content container when trafilatura/readability unavailable.

    Output:
        Best-guess content Tag (may be body).
    """
    for selector in ("main", "article", '[role="main"]', "#content", ".content", ".post-content"):
        node = soup.select_one(selector)
        if node and len(node.get_text(strip=True)) > 200:
            return node
    # Largest text block among divs
    candidates = soup.find_all(["article", "div", "section"])
    best: Optional[Tag] = None
    best_len = 0
    for node in candidates:
        text_len = len(node.get_text(strip=True))
        if text_len > best_len:
            best_len = text_len
            best = node
    if best and best_len > 200:
        return best
    body = soup.body or soup
    return body


def _cell_text(cell: Tag) -> str:
    """Flatten table cell to plain text."""
    return re.sub(r"\s+", " ", cell.get_text(" ", strip=True))


def _table_to_markdown(table: Tag) -> str:
    """
    Convert HTML table to GitHub-flavored Markdown table.

    Output:
        Markdown table string or empty when invalid.
    """
    rows: List[List[str]] = []
    for tr in table.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        if cells:
            rows.append([_cell_text(c) for c in cells])
    if not rows:
        return ""
    col_count = max(len(r) for r in rows)
    normalized = [r + [""] * (col_count - len(r)) for r in rows]
    header = normalized[0]
    sep = ["---"] * col_count
    body_rows = normalized[1:] if len(normalized) > 1 else []
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(sep) + " |",
    ]
    for row in body_rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _inline_markdown(node: Tag, base_url: str) -> str:
    """
    Render inline / block nodes to Markdown recursively.

    Input:
        node: BeautifulSoup Tag.
        base_url: Page URL for resolving relative links.

    Output:
        Markdown fragment string.
    """
    if isinstance(node, NavigableString):
        return unescape(str(node))

    if not isinstance(node, Tag):
        return ""

    name = node.name.lower()
    if name in _NOISE_TAGS:
        return ""

    if name in ("h1", "h2", "h3", "h4", "h5", "h6"):
        level = int(name[1])
        inner = "".join(_inline_markdown(c, base_url) for c in node.children).strip()
        return f"\n\n{'#' * level} {inner}\n\n"

    if name == "p":
        inner = "".join(_inline_markdown(c, base_url) for c in node.children).strip()
        return f"\n\n{inner}\n\n" if inner else ""

    if name in ("strong", "b"):
        inner = "".join(_inline_markdown(c, base_url) for c in node.children).strip()
        return f"**{inner}**" if inner else ""

    if name in ("em", "i"):
        inner = "".join(_inline_markdown(c, base_url) for c in node.children).strip()
        return f"*{inner}*" if inner else ""

    if name == "a":
        href = node.get("href") or ""
        if href and not href.startswith(("#", "javascript:")):
            href = urljoin(base_url, href)
        inner = "".join(_inline_markdown(c, base_url) for c in node.children).strip()
        return f"[{inner}]({href})" if inner and href else inner

    if name in ("ul", "ol"):
        items: List[str] = []
        ordered = name == "ol"
        for idx, li in enumerate(node.find_all("li", recursive=False), start=1):
            item_text = "".join(_inline_markdown(c, base_url) for c in li.children).strip()
            prefix = f"{idx}." if ordered else "-"
            items.append(f"{prefix} {item_text}")
        return "\n" + "\n".join(items) + "\n"

    if name == "br":
        return "\n"

    if name == "table":
        return "\n\n" + _table_to_markdown(node) + "\n\n"

    if name in ("div", "section", "article", "span", "blockquote", "li"):
        return "".join(_inline_markdown(c, base_url) for c in node.children)

    return node.get_text(" ", strip=True)


def _html_fragment_to_markdown(html: str, base_url: str) -> str:
    """
    Convert HTML fragment to Markdown preserving structure.

    Output:
        Cleaned Markdown body text.
    """
    soup = BeautifulSoup(html, "lxml")
    root = soup.body or soup
    _strip_noise(root)
    md = _inline_markdown(root, base_url)
    md = re.sub(r"\n{3,}", "\n\n", md)
    md = re.sub(r"[ \t]+\n", "\n", md)
    return md.strip()


def _fix_unicode_escapes(text: str) -> str:
    """
    Decode literal \\uXXXX sequences some extractors emit for non-ASCII text.

    Output:
        UTF-8 string with actual Persian/Unicode characters.
    """
    if not re.search(r"\\u[0-9a-fA-F]{4}", text):
        return text
    try:
        return text.encode("utf-8").decode("unicode_escape")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return text


def _extract_with_trafilatura(html: str, url: str) -> Optional[str]:
    """Try trafilatura markdown extraction."""
    if not _HAS_TRAFILATURA:
        return None
    try:
        downloaded = trafilatura.extract(
            html,
            url=url,
            output_format="markdown",
            include_links=True,
            include_tables=True,
            include_formatting=True,
            favor_precision=True,
        )
        if downloaded and len(downloaded.strip()) >= 50:
            return downloaded.strip()
    except Exception as exc:
        logger.debug("trafilatura failed for %s: %s", url, exc)
    return None


def _extract_with_readability(html: str, url: str) -> Optional[str]:
    """Try readability-lxml main content HTML then convert to Markdown."""
    if not _HAS_READABILITY:
        return None
    try:
        doc = ReadabilityDocument(html)
        summary_html = doc.summary(html_partial=True)
        if summary_html:
            md = _html_fragment_to_markdown(summary_html, url)
            if len(md.strip()) >= 50:
                return md.strip()
    except Exception as exc:
        logger.debug("readability failed for %s: %s", url, exc)
    return None


def _extract_with_heuristic(html: str, url: str) -> str:
    """Fallback BeautifulSoup main-content heuristic."""
    soup = BeautifulSoup(html, "lxml")
    main = _pick_main_node(soup)
    _strip_noise(main)
    return _inline_markdown(main, url).strip()


def detect_boilerplate_lines(documents: List[str], min_ratio: float = 0.5) -> Set[str]:
    """
    Find repeated lines across many pages (headers/footers).

    Input:
        documents: List of Markdown bodies.
        min_ratio: Line must appear on at least this fraction of docs.

    Output:
        Set of boilerplate lines to remove.
    """
    if len(documents) < 3:
        return set()
    line_counts: dict[str, int] = {}
    threshold = max(2, int(len(documents) * min_ratio))
    for doc in documents:
        seen_in_doc: Set[str] = set()
        for line in doc.splitlines():
            normalized = line.strip()
            if len(normalized) < 20:
                continue
            if normalized not in seen_in_doc:
                seen_in_doc.add(normalized)
                line_counts[normalized] = line_counts.get(normalized, 0) + 1
    return {line for line, count in line_counts.items() if count >= threshold}


def strip_boilerplate(text: str, boilerplate: Set[str]) -> str:
    """
    Remove known boilerplate lines from Markdown body.

    Output:
        Text with repeated lines filtered out.
    """
    if not boilerplate:
        return text
    kept: List[str] = []
    for line in text.splitlines():
        if line.strip() in boilerplate:
            continue
        kept.append(line)
    return "\n".join(kept).strip()


def extract_page_content(html: bytes, url: str) -> ExtractedPage:
    """
    Extract main content and metadata from HTML.

    Input:
        html: Raw page bytes (UTF-8).
        url: Canonical page URL.

    Output:
        ExtractedPage with Markdown body and metadata fields.
    """
    decoded = html.decode("utf-8", errors="replace")
    soup = BeautifulSoup(decoded, "lxml")
    title = _page_title(soup)
    description = _meta_description(soup)

    markdown = _extract_with_trafilatura(decoded, url)
    if not markdown:
        markdown = _extract_with_readability(decoded, url)
    if not markdown:
        markdown = _extract_with_heuristic(decoded, url)

    markdown = _fix_unicode_escapes(markdown)
    lang = _detect_lang(soup, markdown)
    if not title and markdown.startswith("#"):
        first_line = markdown.split("\n", 1)[0]
        title = first_line.lstrip("#").strip()

    return ExtractedPage(
        url=url,
        title=title or urlparse(url).path.rstrip("/").split("/")[-1] or url,
        description=description,
        lang=lang,
        markdown=markdown,
        char_count=len(markdown),
    )
