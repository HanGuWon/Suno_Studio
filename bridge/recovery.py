from __future__ import annotations

from collections.abc import Callable

from bridge.models import Job, JobStatus
from storage.durable_storage import DurableStorage


class StartupRecoveryWorker:
    """Restores in-flight jobs and hands them back to orchestration logic."""

    def __init__(
        self,
        storage: DurableStorage,
        *,
        resume_polling: Callable[[Job], None],
        resume_download: Callable[[Job], None],
    ) -> None:
        self.storage = storage
        self.resume_polling = resume_polling
        self.resume_download = resume_download

    def run_once(self) -> list[str]:
        recovered: list[str] = []
        for job in self.storage.list_in_flight_jobs():
            if job.status in {JobStatus.CREATED, JobStatus.SUBMITTED, JobStatus.POLLING}:
                self.resume_polling(job)
            elif job.status is JobStatus.DOWNLOADING:
                self.resume_download(job)
            recovered.append(job.id)
        return recovered
