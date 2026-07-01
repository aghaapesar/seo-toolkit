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


def test_import_from_txt_files_merges_multiple(tmp_path):
    """Batch import should merge URLs from several text files."""
    file_a = tmp_path / "batch_a.txt"
    file_b = tmp_path / "batch_b.txt"
    file_a.write_text("https://example.com/a\nhttps://example.com/b\n", encoding="utf-8")
    file_b.write_text(
        "https://example.com/b\nhttps://example.com/c\n",
        encoding="utf-8",
    )

    tracker = UrlIndexTracker("example.com", base_dir=str(tmp_path / "history"))
    result = tracker.import_from_txt_files([str(file_a), str(file_b)])

    assert result["total_added"] == 3
    assert result["files_processed"] == 2
    assert result["files"][0]["added"] == 2
    assert result["files"][1]["added"] == 1
    assert tracker.get_status()["total_submitted"] == 3


def test_save_sitemap_snapshot_and_pending_batch(tmp_path):
    """Snapshot should persist latest list; pending batch awaits mark."""
    tracker = UrlIndexTracker("example.com", base_dir=str(tmp_path))
    new_urls, _ = tracker.diff(["https://example.com/a", "https://example.com/b"])
    assert len(new_urls) == 2
    assert tracker.sitemap_latest_file.exists()
    assert tracker.get_status()["sitemap_url_count"] == 2

    tracker.set_last_pending_batch(new_urls, "new_urls_test.txt")
    assert tracker.get_status()["has_pending_batch"] is True
    batch_id = tracker.mark_last_pending_batch()
    assert batch_id
    assert tracker.get_status()["has_pending_batch"] is False
    assert tracker.get_status()["total_submitted"] == 2


def test_import_without_mark_adds_diff_exclusions(tmp_path):
    """Import without mark should exclude URLs from diff only."""
    import_file = tmp_path / "old.txt"
    import_file.write_text("https://example.com/old\n", encoding="utf-8")

    tracker = UrlIndexTracker("example.com", base_dir=str(tmp_path / "history"))
    added = tracker.import_from_txt(str(import_file), mark_submitted=False)
    assert added == 1
    assert tracker.get_status()["total_submitted"] == 0
    assert tracker.get_status()["diff_exclusions_count"] == 1

    new_urls, already = tracker.diff(
        ["https://example.com/old", "https://example.com/new"]
    )
    assert new_urls == ["https://example.com/new"]
    assert already == ["https://example.com/old"]


def test_archive_url_status_creates_files(tmp_path):
    """Archive should write url_status csv/json and register export run."""
    tracker = UrlIndexTracker("example.com", base_dir=str(tmp_path))
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    new_urls, already = tracker.diff(["https://example.com/a", "https://example.com/b"])
    tracker.set_last_pending_batch(new_urls, "new_urls_test.txt")
    run = tracker.archive_url_status(
        ["https://example.com/a", "https://example.com/b"],
        new_urls,
        already,
        output_dir,
        "20260101_120000",
    )
    assert run["counts"]["pending_index"] == 2
    assert (tracker.project_dir / "url_status" / "url_status_20260101_120000.csv").exists()
    assert tracker.list_export_runs()[0]["run_id"] == "20260101_120000"


def test_export_txt_writes_one_url_per_line(tmp_path):
    """Export should create newline-delimited URL file."""
    tracker = UrlIndexTracker("example.com", base_dir=str(tmp_path))
    out = tracker.export_txt(
        ["https://example.com/a", "https://example.com/b"],
        Path(tmp_path / "out.txt"),
    )

    content = out.read_text(encoding="utf-8")
    assert content == "https://example.com/a\nhttps://example.com/b\n"
