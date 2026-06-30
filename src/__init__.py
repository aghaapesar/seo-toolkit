"""
Seo Toolkit

Persian-optimized SEO content analyzer and automation toolkit.
"""

from pathlib import Path


def read_version() -> str:
    """Read package version from VERSION file."""
    version_file = Path(__file__).resolve().parent.parent / "VERSION"
    try:
        return version_file.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return "2.5.0"


__version__ = read_version()
__author__ = "Seo Toolkit"
