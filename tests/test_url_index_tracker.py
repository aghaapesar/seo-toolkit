"""Unit tests for UrlIndexTracker."""

from pathlib import Path

from src.services.url_index_tracker import UrlIndexTracker, normalize_url


def test_normalize_url_strips_trailing_slash_and_lowercases_host():
    """URL normalization should stabilize host casing and trailing slashes."""
    assert (
        normalize_url("HTTPS://Example.COM/page/")
        == "https://example.com/page"
    )


def test_diff_splits_new_and_submitted(tmp_path):
    """Diff should separate unseen URLs from submitted history."""
    tracker = UrlIndexTracker("example.com", base_dir=str(tmp_path))
    tracker.mark_batch_submitted(["https://example.com/old"])

    new_urls, already = tracker.diff(
        [
            "https://example.com/old",
            "https://example.com/new",
        ]
    )

    assert new_urls == ["https://example.com/new"]
    assert already == ["https://example.com/old"]


def test_import_from_txt_adds_urls(tmp_path):
    """Import should merge URLs from a text file."""
    import_file = tmp_path / "urls.txt"
    import_file.write_text(
        "https://example.com/a\n# comment\nhttps://example.com/b\n",
        encoding="utf-8",
    )

    tracker = UrlIndexTracker("example.com", base_dir=str(tmp_path / "history"))
    added = tracker.import_from_txt(str(import_file))

    assert added == 2
    assert tracker.get_status()["total_submitted"] == 2


def test_export_txt_writes_one_url_per_line(tmp_path):
    """Export should create newline-delimited URL file."""
    tracker = UrlIndexTracker("example.com", base_dir=str(tmp_path))
    out = tracker.export_txt(
        ["https://example.com/a", "https://example.com/b"],
        Path(tmp_path / "out.txt"),
    )

    content = out.read_text(encoding="utf-8")
    assert content == "https://example.com/a\nhttps://example.com/b\n"
