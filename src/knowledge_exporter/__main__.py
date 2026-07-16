"""
CLI entry point for knowledge_exporter.

Example:
    python -m src.knowledge_exporter \\
        --sitemap https://example.com/sitemap.xml \\
        --output output/knowledge_export \\
        --max-part-kb 500 \\
        --concurrency 4
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from src.cli.logging_setup import configure_logging
from src.knowledge_exporter.config import KnowledgeExporterConfig
from src.knowledge_exporter.exporter import KnowledgeExporter


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Export sitemap pages to RAG-ready Markdown knowledge parts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.knowledge_exporter --sitemap https://example.com/sitemap.xml \\
      --output output/knowledge_export

  python -m src.knowledge_exporter --urls-file urls.txt --output output/kb \\
      --include-pattern '/blog/' --exclude-pattern '/tag/' \\
      --max-part-kb 300 --max-pages-per-part 40 --concurrency 6
        """,
    )
    parser.add_argument("--sitemap", type=str, help="Root sitemap URL")
    parser.add_argument(
        "--urls-file",
        type=str,
        help="Text file with one URL per line (alternative to --sitemap)",
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Output directory for knowledge_part_*.md and index.json",
    )
    parser.add_argument(
        "--max-part-kb",
        type=int,
        default=500,
        help="Max size per part file in KB (default: 500)",
    )
    parser.add_argument(
        "--max-pages-per-part",
        type=int,
        default=50,
        help="Max pages per part file (default: 50)",
    )
    parser.add_argument("--include-pattern", type=str, help="Regex: URL must match")
    parser.add_argument("--exclude-pattern", type=str, help="Regex: URL must not match")
    parser.add_argument("--concurrency", type=int, default=4, help="Parallel workers")
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=0.25,
        help="Seconds delay between request starts (default: 0.25)",
    )
    parser.add_argument("--timeout", type=int, default=45, help="HTTP timeout seconds")
    parser.add_argument("--max-retries", type=int, default=3, help="Retries per URL")
    parser.add_argument(
        "--min-chars",
        type=int,
        default=100,
        help="Min content chars before marking page as empty (default: 100)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    return parser


def _load_urls_file(path: str) -> list[str]:
    """Load URLs from a text file."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]


def main(argv: list[str] | None = None) -> int:
    """
    Run knowledge export from CLI args.

    Output:
        Exit code 0 on success, 1 on fatal error.
    """
    args = build_parser().parse_args(argv)
    configure_logging(verbose=args.verbose)

    urls: list[str] = []
    if args.urls_file:
        urls = _load_urls_file(args.urls_file)
    if not args.sitemap and not urls:
        print("Error: provide --sitemap or --urls-file", file=sys.stderr)
        return 1

    config = KnowledgeExporterConfig(
        output_dir=Path(args.output),
        sitemap_url=args.sitemap or "",
        urls=urls,
        max_part_bytes=args.max_part_kb * 1024,
        max_pages_per_part=args.max_pages_per_part,
        include_pattern=args.include_pattern,
        exclude_pattern=args.exclude_pattern,
        concurrency=args.concurrency,
        rate_limit_seconds=args.rate_limit,
        timeout=args.timeout,
        max_retries=args.max_retries,
        min_content_chars=args.min_chars,
    )

    exporter = KnowledgeExporter(config)
    summary = exporter.run()

    if summary.failed == summary.total_urls and summary.total_urls > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
