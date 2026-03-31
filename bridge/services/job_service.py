from __future__ import annotations

from dataclasses import dataclass
from queue import Empty, Queue
from threading import Event, Lock, Thread
import time
from pathlib import Path
from uuid import uuid4

from bridge.adapters.base import ProviderAdapter
from bridge.downloader import AssetDownloader
from bridge.models import CreateJobRequest, Job, JobStatus, JobType, TERMINAL_STATES
from storage.durable_storage import DurableStorage


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    poll_interval_seconds: float = 0.05
    retry_backoff_seconds: float = 0.05


class CancellationRegistry:
    def __init__(self) -> None:
        self._cancelled: set[str] = set()
        self._lock = Lock()

    def request(self, job_id: str) -> None:
        with self._lock:
            self._cancelled.add(job_id)

    def clear(self, job_id: str) -> None:
        with self._lock:
            self._cancelled.discard(job_id)

    def is_cancelled(self, job_id: str) -> bool:
        with self._lock:
            return job_id in self._cancelled


class JobQueue:
    def __init__(self) -> None:
        self._queue: Queue[str] = Queue()

    def enqueue(self, job_id: str) -> None:
        self._queue.put(job_id)

    def dequeue(self, timeout: float = 0.1) -> str | None:
        try:
            return self._queue.get(timeout=timeout)
        except Empty:
            return None


class JobOrchestrator:
    def __init__(
        self,
        storage: DurableStorage,
        provider: ProviderAdapter,
        downloader: AssetDownloader,
        *,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self.storage = storage
        self.provider = provider
        self.downloader = downloader
        self.retry_policy = retry_policy or RetryPolicy()
        self.queue = JobQueue()
        self.cancellations = CancellationRegistry()
        self._worker = WorkerLoop(self)

    def start(self) -> None:
        self._worker.start()
        self.recover_inflight_jobs()

    def stop(self) -> None:
        self._worker.stop()

    def enqueue_job(self, job_id: str) -> None:
        job = self.storage.get_job(job_id)
        if not job or job.status in TERMINAL_STATES:
            return
        if job.status is JobStatus.CREATED:
            self.storage.set_job_status(job_id, JobStatus.QUEUED_LOCAL, progress=0.0)
        self.queue.enqueue(job_id)

    def recover_inflight_jobs(self) -> list[str]:
        recovered: list[str] = []
        for job in self.storage.list_in_flight_jobs():
            self.queue.enqueue(job.id)
            recovered.append(job.id)
        return recovered

    def cancel_job(self, job_id: str) -> Job:
        job = self.storage.get_job(job_id)
        if not job:
            raise KeyError(f"unknown job {job_id}")
        if job.status in TERMINAL_STATES:
            return job
        self.cancellations.request(job_id)
        if job.remote_job_id:
            self.provider.cancel_remote_job(job.remote_job_id)
            return self.storage.set_job_status(job_id, JobStatus.CANCELLING, reason="cancel requested")
        return self.storage.set_job_status(job_id, JobStatus.CANCELLED, reason="cancelled before remote submit")

    def process_one(self, job_id: str) -> None:
        job = self.storage.get_job(job_id)
        if not job or job.status in TERMINAL_STATES:
            return

        if self.cancellations.is_cancelled(job_id):
            self.storage.set_job_status(job_id, JobStatus.CANCELLED, reason="cancelled before processing", progress=job.progress)
            self.cancellations.clear(job_id)
            return

        if not job.remote_job_id:
            self._submit_remote(job)
            job = self.storage.get_job(job_id)
            if not job:
                return

        self._poll_and_download(job)

    def _submit_remote(self, job: Job) -> None:
        current = self.storage.get_job(job.id)
        if not current or current.status in TERMINAL_STATES:
            return
        if current.status in {JobStatus.CANCELLING, JobStatus.CANCELLED}:
            self.storage.set_job_status(job.id, JobStatus.CANCELLED, reason="cancelled before submit")
            return
        try:
            self.storage.set_job_status(job.id, JobStatus.SUBMITTING_REMOTE, progress=0.05)
        except ValueError:
            return

        if self.cancellations.is_cancelled(job.id):
            self.storage.set_job_status(job.id, JobStatus.CANCELLED, reason="cancelled before submit", progress=0.05)
            self.cancellations.clear(job.id)
            return

        if job.type is JobType.TEXT:
            remote_id = self.provider.submit_text_job(
                job_id=job.id,
                prompt=job.payload.get("prompt", ""),
                metadata=job.payload.get("metadata", {}),
            )
        else:
            asset_id = job.asset_id or job.payload.get("assetId")
            if not asset_id:
                self.storage.set_job_status(job.id, JobStatus.FAILED, reason="missing audio asset", last_error="missing audio asset")
                return
            manifest = self.storage.get_imported_asset(asset_id)
            if not manifest:
                self.storage.set_job_status(job.id, JobStatus.FAILED, reason="asset not found", last_error="asset not found")
                return
            remote_id = self.provider.submit_audio_job(
                job_id=job.id,
                prompt=job.payload.get("prompt", ""),
                metadata=job.payload.get("metadata", {}),
                source_path=Path(manifest["original"]["path"]),
            )

        self.storage.set_job_status(job.id, JobStatus.POLLING_REMOTE, remote_job_id=remote_id, progress=0.1)

    def _poll_and_download(self, job: Job) -> None:
        current = self.storage.get_job(job.id)
        if not current or current.status in TERMINAL_STATES or not current.remote_job_id:
            return

        attempts = current.attempts
        while attempts < self.retry_policy.max_attempts:
            if self.cancellations.is_cancelled(job.id):
                self.provider.cancel_remote_job(current.remote_job_id)
                self.storage.set_job_status(job.id, JobStatus.CANCELLED, reason="cancelled during polling", progress=current.progress)
                self.cancellations.clear(job.id)
                return

            poll = self.provider.poll_job(current.remote_job_id)
            if poll.state == "retryable_error":
                attempts += 1
                self.storage.update_job_runtime_fields(job.id, progress=poll.progress, last_error=poll.retryable_error)
                self.storage.update_job_runtime_fields(job.id, progress=poll.progress)
                self.storage.set_job_status(
                    job.id,
                    JobStatus.POLLING_REMOTE,
                    reason="retryable provider error",
                    progress=poll.progress,
                    last_error=poll.retryable_error,
                    attempts_increment=1,
                )
                time.sleep(self.retry_policy.retry_backoff_seconds)
                continue

            if poll.state in {"queued", "in_progress"}:
                self.storage.update_job_runtime_fields(job.id, progress=poll.progress)
                time.sleep(self.retry_policy.poll_interval_seconds)
                current = self.storage.get_job(job.id)
                if not current:
                    return
                continue

            if poll.state == "cancelled":
                self.storage.set_job_status(job.id, JobStatus.CANCELLED, reason="provider cancelled", progress=poll.progress)
                return

            if poll.state != "ready":
                self.storage.set_job_status(job.id, JobStatus.FAILED, reason=f"unexpected provider state: {poll.state}", last_error=poll.state)
                return

            self.storage.set_job_status(job.id, JobStatus.DOWNLOADING, progress=0.95)
            outputs = self.provider.download_outputs(current.remote_job_id)
            files: list[dict[str, str]] = []
            output_assets: list[str] = []
            for output in outputs:
                path, _ = self.downloader.store_download(
                    job_id=job.id,
                    variant=output.variant,
                    content=output.content,
                    ext=output.extension,
                )
                files.append({"variant": output.variant, "path": str(path)})
                output_assets.append(str(path))

            self.storage.attach_job_artifacts(job.id, output_manifest={"files": files}, output_assets=output_assets)
            self.storage.set_job_status(job.id, JobStatus.COMPLETE, progress=1.0, last_error=None)
            return

        self.storage.set_job_status(job.id, JobStatus.FAILED, reason="retry attempts exhausted", last_error="retry attempts exhausted")


class WorkerLoop:
    def __init__(self, orchestrator: JobOrchestrator) -> None:
        self.orchestrator = orchestrator
        self._stop_event = Event()
        self._thread: Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = Thread(target=self._run, name="bridge-worker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _run(self) -> None:
        while not self._stop_event.is_set():
            job_id = self.orchestrator.queue.dequeue(timeout=0.1)
            if not job_id:
                continue
            try:
                self.orchestrator.process_one(job_id)
            except Exception:
                # Worker should stay alive; per-job errors are persisted by orchestrator paths.
                continue


class JobService:
    def __init__(self, storage: DurableStorage, orchestrator: JobOrchestrator) -> None:
        self.storage = storage
        self.orchestrator = orchestrator

    def create_text_job(self, request: CreateJobRequest) -> tuple[Job, bool]:
        return self._create_job(job_type=JobType.TEXT, request=request, asset_id=None)

    def create_audio_job(self, request: CreateJobRequest, *, asset_id: str | None = None) -> tuple[Job, bool]:
        return self._create_job(job_type=JobType.AUDIO, request=request, asset_id=asset_id)

    def _create_job(self, *, job_type: JobType, request: CreateJobRequest, asset_id: str | None) -> tuple[Job, bool]:
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
        persisted, created = self.storage.create_job_idempotent(job)
        if created:
            self.orchestrator.enqueue_job(persisted.id)
        return persisted, created

    def cancel_job(self, job_id: str) -> Job:
        return self.orchestrator.cancel_job(job_id)
