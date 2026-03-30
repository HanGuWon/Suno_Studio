from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from bridge.adapters.base import ProviderAdapter
from bridge.downloader import AssetDownloader
from bridge.models import CreateJobRequest, Job, JobStatus, JobType
from storage.durable_storage import DurableStorage


class JobService:
    def __init__(
        self,
        storage: DurableStorage,
        provider: ProviderAdapter,
        downloader: AssetDownloader,
    ) -> None:
        self.storage = storage
        self.provider = provider
        self.downloader = downloader

    def create_text_job(self, request: CreateJobRequest) -> tuple[Job, bool]:
        return self._create_job(job_type=JobType.TEXT, request=request, asset_id=None)

    def create_audio_job(self, request: CreateJobRequest, *, asset_id: str | None = None) -> tuple[Job, bool]:
        return self._create_job(job_type=JobType.AUDIO, request=request, asset_id=asset_id)

    def _create_job(self, *, job_type: JobType, request: CreateJobRequest, asset_id: str | None) -> tuple[Job, bool]:
        existing = self.storage.get_job_by_request_id(job_type, request.clientRequestId)
        if existing:
            return existing, False

        payload = {"prompt": request.prompt, "metadata": request.metadata}
        if asset_id:
            payload["assetId"] = asset_id

        job = Job(
            id=str(uuid4()),
            type=job_type,
            status=JobStatus.CREATED,
            client_request_id=request.clientRequestId,
            payload=payload,
            asset_id=asset_id,
        )
        self.storage.create_job(job)
        return job, True

    def run_job(self, job_id: str) -> Job:
        job = self.storage.get_job(job_id)
        if not job:
            raise KeyError(f"unknown job {job_id}")
        if job.status in {JobStatus.COMPLETE, JobStatus.FAILED, JobStatus.CANCELLED}:
            return job

        self.storage.set_job_status(job.id, JobStatus.SUBMITTED)
        if job.type is JobType.TEXT:
            remote_id = self.provider.submit_text_job(
                job_id=job.id,
                prompt=job.payload.get("prompt", ""),
                metadata=job.payload.get("metadata", {}),
            )
        else:
            asset_id = job.asset_id or job.payload.get("assetId")
            if not asset_id:
                raise ValueError("audio job missing imported asset id")
            manifest = self.storage.get_imported_asset(asset_id)
            if not manifest:
                raise ValueError(f"unknown asset id {asset_id}")
            remote_id = self.provider.submit_audio_job(
                job_id=job.id,
                prompt=job.payload.get("prompt", ""),
                metadata=job.payload.get("metadata", {}),
                source_path=Path(manifest["original"]["path"]),
            )

        self.storage.set_job_status(job.id, JobStatus.POLLING, remote_provider_id=remote_id)
        poll_status = self.provider.poll_job(remote_id)
        if poll_status != "ready":
            return self.storage.set_job_status(job.id, JobStatus.FAILED, reason=f"provider status: {poll_status}")

        self.storage.set_job_status(job.id, JobStatus.DOWNLOADING)
        outputs = self.provider.download_outputs(remote_id)
        files: list[dict[str, str]] = []
        for output in outputs:
            path, _ = self.downloader.store_download(
                job_id=job.id,
                variant=output.variant,
                content=output.content,
                ext=output.extension,
            )
            files.append({"variant": output.variant, "path": str(path)})

        self.storage.attach_job_artifacts(job.id, output_manifest={"files": files})
        return self.storage.set_job_status(job.id, JobStatus.COMPLETE)

    def cancel_job(self, job_id: str) -> Job:
        job = self.storage.get_job(job_id)
        if not job:
            raise KeyError(f"unknown job {job_id}")
        if job.status in {JobStatus.COMPLETE, JobStatus.FAILED, JobStatus.CANCELLED}:
            return job
        return self.storage.set_job_status(job_id, JobStatus.CANCELLED, reason="cancel requested")

    def recover_inflight(self) -> list[str]:
        recovered: list[str] = []
        for job in self.storage.list_in_flight_jobs():
            self.run_job(job.id)
            recovered.append(job.id)
        return recovered
