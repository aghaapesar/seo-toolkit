"""Tests for background job manager."""

from web.app.services.job_manager import JobManager


def test_create_job_and_progress():
    """Jobs should be created and accept progress updates."""
    mgr = JobManager()
    job = mgr.create("index_diff", {"domain": "example.com"}, initial_status="waiting_client")
    assert job.status == "waiting_client"
    assert job.progress == 0

    mgr.update_progress(job.id, 42, "Fetching sub-sitemap 2/5", step="sub_2")
    updated = mgr.require(job.id)
    assert updated.progress == 42
    assert updated.message == "Fetching sub-sitemap 2/5"
    assert len(updated.steps) == 1


def test_job_to_dict_hides_large_params():
    """Serialized jobs should not expose raw URL lists."""
    mgr = JobManager()
    job = mgr.create("index_diff", {"domain": "x.com", "urls": ["https://x.com/a"]})
    data = job.to_dict()
    assert "urls" not in data["params"]
    assert data["job_type"] == "index_diff"
