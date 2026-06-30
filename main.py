#!/usr/bin/env python3
"""
Seo Toolkit - CLI entry point.

Persian-optimized SEO tooling: Search Console analysis, sitemap scraping,
AI content generation, internal linking, synonym finder, and URL index diff.
"""

import argparse
import logging
import sys
from pathlib import Path

from src.app.toolkit import SeoToolkit
from src.cli.logging_setup import configure_logging
from src.cli.prompts import select_mode_interactive

logger = logging.getLogger(__name__)

MODE_CHOICES = [
    "content",
    "scraping",
    "generation",
    "linking",
    "synonyms",
    "index-diff",
]


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Seo Toolkit - Persian SEO analysis and automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s
  %(prog)s --mode content --test
  %(prog)s --mode index-diff --domain example.com
  %(prog)s --mode index-diff --import previous_urls.txt --domain example.com
        """,
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=MODE_CHOICES,
        help="Operational mode",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Process only 10 items for quick validation",
    )
    parser.add_argument(
        "--domain",
        type=str,
        help="Domain/project name for index-diff mode",
    )
    parser.add_argument(
        "--import",
        dest="import_file",
        type=str,
        help="Import previously submitted URLs from a text file (index-diff)",
    )
    parser.add_argument(
        "--mark-submitted",
        action="store_true",
        help="Mark exported new URLs as submitted (index-diff)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser


def main() -> None:
    """Parse CLI args and dispatch the selected mode."""
    args = build_parser().parse_args()
    configure_logging(verbose=args.verbose)

    if args.verbose:
        logger.debug("Verbose logging enabled")

    if not Path(args.config).exists():
        print(f"\nConfiguration file '{args.config}' not found")
        print("Copy config.sample.yaml to config.yaml and add your API keys.\n")
        sys.exit(1)

    mode = args.mode or select_mode_interactive()
    toolkit = SeoToolkit(config_path=args.config)

    if mode == "content":
        toolkit.run_content_optimization(test_mode=args.test)
    elif mode == "scraping":
        toolkit.run_seo_data_collection(test_mode=args.test)
    elif mode == "generation":
        toolkit.run_content_generation()
    elif mode == "linking":
        toolkit.run_internal_linking_only()
    elif mode == "synonyms":
        toolkit.run_synonym_finder()
    elif mode == "index-diff":
        toolkit.run_index_diff(
            domain=args.domain,
            import_file=args.import_file,
            mark_submitted=args.mark_submitted,
        )


if __name__ == "__main__":
    main()
