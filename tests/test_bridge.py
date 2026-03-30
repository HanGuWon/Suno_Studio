from uuid import uuid4

from bridge.api import BridgeAPI
from bridge.downloader import AssetDownloader
from bridge.models import CreateJobRequest, JobStatus
from bridge.recovery import StartupRecoveryWorker
from plugin.session_state import APVTSSessionState
from storage.durable_storage import DurableStorage


def test_idempotent_create_for_text_and_audio(tmp_path):
    storage = DurableStorage(tmp_path / "jobs.db")
    api = BridgeAPI(storage)

    request_id = uuid4()
    request = CreateJobRequest(prompt="hello", clientRequestId=request_id)
    first, created = api.post_jobs_text(request)
    second, created_again = api.post_jobs_text(request)

    assert created is True
    assert created_again is False
    assert first.id == second.id

    audio_request = CreateJobRequest(prompt="sound", clientRequestId=request_id)
    audio, audio_created = api.post_jobs_audio(audio_request)
    assert audio_created is True
    assert audio.type.value == "audio"


def test_persist_transitions_and_remote_id(tmp_path):
    storage = DurableStorage(tmp_path / "jobs.db")
    api = BridgeAPI(storage)
    job, _ = api.post_jobs_text(CreateJobRequest(prompt="x", clientRequestId=uuid4()))

    updated = storage.set_job_status(job.id, JobStatus.SUBMITTED, remote_provider_id="provider-123")
    assert updated.remote_provider_id == "provider-123"
    assert updated.status is JobStatus.SUBMITTED


def test_recovery_worker_rehydrates_inflight_jobs(tmp_path):
    storage = DurableStorage(tmp_path / "jobs.db")
    api = BridgeAPI(storage)
    created, _ = api.post_jobs_text(CreateJobRequest(prompt="x", clientRequestId=uuid4()))
    downloading, _ = api.post_jobs_audio(CreateJobRequest(prompt="y", clientRequestId=uuid4()))
    storage.set_job_status(downloading.id, JobStatus.DOWNLOADING)

    polled: list[str] = []
    downloaded: list[str] = []
    worker = StartupRecoveryWorker(
        storage,
        resume_polling=lambda job: polled.append(job.id),
        resume_download=lambda job: downloaded.append(job.id),
    )

    recovered = worker.run_once()
    assert created.id in polled
    assert downloading.id in downloaded
    assert set(recovered) == {created.id, downloading.id}


def test_download_dedup_uses_job_variant_checksum(tmp_path):
    storage = DurableStorage(tmp_path / "jobs.db")
    downloader = AssetDownloader(storage, root=tmp_path / "assets")

    path1, inserted1 = downloader.store_download(job_id="job1", variant="main", content=b"abc", ext="wav")
    path2, inserted2 = downloader.store_download(job_id="job1", variant="main", content=b"abc", ext="wav")

    assert inserted1 is True
    assert inserted2 is False
    assert path1 == path2


def test_plugin_state_generates_and_reconciles_without_duplicates(tmp_path):
    storage = DurableStorage(tmp_path / "jobs.db")
    api = BridgeAPI(storage)
    session = APVTSSessionState(state_path=tmp_path / "session.json")
    session.load()

    request_id = session.ensure_request_id("submit-1")
    same_request_id = session.ensure_request_id("submit-1")
    assert request_id == same_request_id

    job, _ = api.post_jobs_text(CreateJobRequest(prompt="melody", clientRequestId=request_id))
    session.mark_job("submit-1", job_id=job.id)
    storage.set_job_status(job.id, JobStatus.COMPLETE)

    reconciled = session.reconcile_unresolved(storage)
    assert len(reconciled) == 1
    assert reconciled[0].resolved is True
