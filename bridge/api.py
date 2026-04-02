from __future__ import annotations

from bridge.models import CreateJobRequest, Job
from bridge.services.job_service import JobService


class BridgeAPI:
    """Programmatic API used by tests and non-HTTP callers."""

    def __init__(self, job_service: JobService) -> None:
        self.job_service = job_service

    def post_jobs_text(self, request: CreateJobRequest) -> tuple[Job, bool]:
        return self.job_service.create_text_job(request)

    def post_jobs_audio(self, request: CreateJobRequest, *, asset_id: str | None = None) -> tuple[Job, bool]:
        return self.job_service.create_audio_job(request, asset_id=asset_id)

    def post_cancel_job(self, job_id: str) -> Job:
        return self.job_service.cancel_job(job_id)
