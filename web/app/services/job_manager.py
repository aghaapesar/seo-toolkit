"""In-memory background job queue for long-running web tasks."""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional


JobStatus = str  # waiting_client | queued | running | completed | failed


def _utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


@dataclass
class JobRecord:
    """
    Track one background task from creation to completion.

    Input:
        job_type: Logical task name (e.g. index_diff).
        params: Serializable parameters for the worker.

    Output:
        Mutable job state exposed via API polling.
    """

    id: str
    job_type: str
    status: JobStatus
    progress: int = 0
    message: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    steps: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize job for JSON API responses."""
        return {
            "id": self.id,
            "job_type": self.job_type,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "params": {
                k: v
                for k, v in self.params.items()
                if k not in ("urls", "sitemap_file_path")
            },
            "result": self.result,
            "error": self.error,
            "steps": self.steps,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def set_progress(self, percent: int, message: str, step: Optional[str] = None) -> None:
        """Update progress percentage and optional step label."""
        self.progress = max(0, min(100, int(percent)))
        self.message = message
        self.updated_at = _utc_now()
        if step:
            self.steps.append(
                {
                    "label": step,
                    "at": self.updated_at.isoformat(),
                    "progress": self.progress,
                }
            )


class JobManager:
    """
    Thread-safe job registry with a simple background worker pool.

    Input:
        Worker callables receive a JobRecord and mutate it in-place.

    Output:
        Job IDs for clients to poll until completed or failed.
    """

    def __init__(self) -> None:
        self._jobs: Dict[str, JobRecord] = {}
        self._lock = threading.Lock()

    def _get_unlocked(self, job_id: str) -> Optional[JobRecord]:
        """Return a job without acquiring the lock (caller must hold it)."""
        return self._jobs.get(job_id)

    def create(
        self,
        job_type: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        initial_status: JobStatus = "queued",
        message: str = "",
    ) -> JobRecord:
        """Create a new job and store it in memory."""
        job_id = uuid.uuid4().hex
        job = JobRecord(
            id=job_id,
            job_type=job_type,
            status=initial_status,
            params=dict(params or {}),
            message=message,
        )
        with self._lock:
            self._jobs[job_id] = job
        return job

    def get(self, job_id: str) -> Optional[JobRecord]:
        """Return a job by id or None."""
        with self._lock:
            return self._jobs.get(job_id)

    def require(self, job_id: str) -> JobRecord:
        """Return a job or raise KeyError."""
        job = self.get(job_id)
        if not job:
            raise KeyError(job_id)
        return job

    def update_progress(
        self,
        job_id: str,
        percent: int,
        message: str,
        *,
        step: Optional[str] = None,
    ) -> JobRecord:
        """Update progress fields on an existing job."""
        with self._lock:
            job = self._get_unlocked(job_id)
            if not job:
                raise KeyError(job_id)
            job.set_progress(percent, message, step=step)
            return job

    def enqueue(self, job_id: str, worker: Callable[[JobRecord], None]) -> None:
        """Run worker in a daemon thread for the given job."""

        def _run() -> None:
            with self._lock:
                job = self._get_unlocked(job_id)
                if not job:
                    return
                job.status = "running"
                job.updated_at = _utc_now()
            try:
                worker(job)
                with self._lock:
                    job = self._get_unlocked(job_id)
                    if job and job.status == "running":
                        job.status = "completed"
                        job.progress = 100
                        job.updated_at = _utc_now()
            except Exception as exc:  # noqa: BLE001 — surface to API
                with self._lock:
                    job = self._get_unlocked(job_id)
                    if job:
                        job.status = "failed"
                        job.error = str(exc)
                        job.updated_at = _utc_now()

        thread = threading.Thread(target=_run, name=f"job-{job_id[:8]}", daemon=True)
        thread.start()


# Shared singleton for the web process.
job_manager = JobManager()
