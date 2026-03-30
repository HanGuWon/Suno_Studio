from __future__ import annotations

from uuid import uuid4

from bridge.models import CreateJobRequest, Job, JobStatus, JobType
from storage.durable_storage import DurableStorage


class BridgeAPI:
    def __init__(self, storage: DurableStorage) -> None:
        self.storage = storage

    def post_jobs_text(self, request: CreateJobRequest) -> tuple[Job, bool]:
        return self._create_idempotent_job(job_type=JobType.TEXT, request=request)

    def post_jobs_audio(self, request: CreateJobRequest) -> tuple[Job, bool]:
        return self._create_idempotent_job(job_type=JobType.AUDIO, request=request)

    def _create_idempotent_job(self, *, job_type: JobType, request: CreateJobRequest) -> tuple[Job, bool]:
        existing = self.storage.get_job_by_request_id(job_type, request.clientRequestId)
        if existing:
            return existing, False

        job = Job(
            id=str(uuid4()),
            type=job_type,
            status=JobStatus.CREATED,
            client_request_id=request.clientRequestId,
            payload={"prompt": request.prompt, "metadata": request.metadata},
        )
        self.storage.create_job(job)
        return job, True
